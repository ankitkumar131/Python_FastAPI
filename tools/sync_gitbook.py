"""Publish GitBook course copies from public GitHub repositories without executing them.

python tools/sync_gitbook.py --refresh   # Fetch selected branch commits with gh.
python tools/sync_gitbook.py            # Regenerate dashboard/navigation offline.
python tools/sync_gitbook.py --check    # Read-only validation; no network required.

Sources stay in their original repositories. Imported files are generated publication
copies, not an independent two-way GitBook connection to those repositories.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import html
import io
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import tarfile
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / 'notes'
LINK = re.compile(r'(?<!!)\[([^\]\n]+)\]\(([^\s)]+)\)')
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prose_map(text: str, transform) -> str:
    """Transform prose only; leave fenced examples (including four-backtick fences) intact."""
    result, pending = [], []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = FENCE.match(line)
        if fence is not None:
            result.append(line)
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
        elif marker:
            result.append(transform(''.join(pending)))
            pending.clear()
            result.append(line)
            fence = marker[1]
        else:
            pending.append(line)
    result.append(transform(''.join(pending)))
    return ''.join(result)


def local_target(source: str, href: str) -> str | None:
    parsed = urlsplit(html.unescape(href))
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    return posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(parsed.path)))


def adapt_links(path: str, text: str, available: set[str]) -> tuple[str, list[dict]]:
    """Mark absent upstream chapters as unavailable, rather than inventing pages/404 links."""
    missing = []

    def rewrite(prose):
        # Inline code is instructional text, not navigation.
        pieces = re.split(r'(`+[^`\n]*`+)', prose)
        for index in range(0, len(pieces), 2):
            def replace(match):
                label, href = match.groups()
                target = local_target(path, href)
                if target is None or target in available:
                    return match[0]
                missing.append({'file': path, 'target': href})
                return f'{label} *(not available in this published source revision)*'
            pieces[index] = LINK.sub(replace, pieces[index])
        return ''.join(pieces)

    return prose_map(text, rewrite), missing


def read_archive(data: bytes, patterns: list[str]) -> dict[str, bytes]:
    """Read allowlisted regular Markdown members; never extract paths or execute source code."""
    selected = {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        for number, member in enumerate(archive):
            if number > 5000:
                raise ValueError('Source archive exceeds the file-count safety limit')
            parts = PurePosixPath(member.name).parts
            if member.name.startswith('/') or '..' in parts:
                raise ValueError('Unsafe archive path')
            path = '/'.join(parts[1:])
            if not path or not any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns):
                continue
            if not member.isfile() or not path.endswith('.md'):
                raise ValueError(f'Only regular Markdown chapter files may be imported: {path}')
            if path in selected or member.size > 3_000_000:
                raise ValueError(f'Duplicate or oversized chapter: {path}')
            total += member.size
            if total > 25_000_000:
                raise ValueError('Selected documentation exceeds the 25 MB safety limit')
            stream = archive.extractfile(member)
            assert stream is not None
            content = stream.read()
            content.decode('utf-8')
            selected[path] = content
    if not selected:
        raise ValueError('No existing Markdown chapters matched the source include patterns')
    return dict(sorted(selected.items()))


def destination(course: dict) -> Path:
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', course['id']):
        raise ValueError('Course IDs must be lowercase URL slugs')
    return NOTES / 'courses' / course['id']


def manifest_for(course: dict) -> dict:
    return json.loads((destination(course) / 'source.json').read_text())


def assert_unedited(course: dict) -> None:
    folder = destination(course)
    if not folder.exists():
        return
    manifest = manifest_for(course)
    for name, record in manifest['files'].items():
        path = folder / name
        if not path.is_file() or digest(path.read_bytes()) != record['published_sha256']:
            raise ValueError(f'{path.relative_to(ROOT)} was edited locally; preserve that edit before refreshing')


def refresh(course: dict) -> None:
    assert_unedited(course)
    repo = course['repository']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Expected a GitHub owner/repository name')
    response = subprocess.check_output(['gh', 'api', f'repos/{repo}/commits/{quote(course["branch"], safe="")}'])
    sha = json.loads(response)['sha']
    if not re.fullmatch(r'[a-f0-9]{40}', sha):
        raise ValueError('GitHub did not return a valid immutable commit SHA')
    data = subprocess.check_output(['gh', 'api', f'repos/{repo}/tarball/{sha}'])
    if len(data) > 25_000_000:
        raise ValueError('Source archive exceeds the compressed-size safety limit')
    original = read_archive(data, course['include'])
    available = set(original) | {'README.md'}  # A truthful local overview replaces the upstream roadmap.
    published, missing, records = {}, [], {}
    for name, raw in original.items():
        text, absent = adapt_links(name, raw.decode('utf-8'), available)
        published[name] = text.encode('utf-8')
        records[name] = {'source_sha256': digest(raw), 'published_sha256': digest(published[name])}
        missing.extend(absent)
    folder = destination(course)
    if folder.exists():
        previous = manifest_for(course)
        for old in set(previous['files']) - set(published):
            (folder / old).unlink()  # Only previously managed, verified-unedited chapters are removed.
    for name, content in published.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    manifest = {'repository': repo, 'branch': course['branch'], 'commit': sha,
                'files': records, 'unavailable_links': missing}
    (folder / 'source.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(f'Imported {len(records)} chapters from {repo}@{sha}; marked {len(missing)} unavailable references.')


def title(path: Path) -> str:
    match = re.search(r'^#\s+(.+)$', path.read_text(), re.M)
    return match[1].strip() if match else path.stem.replace('-', ' ')


def render(config: dict) -> dict[Path, str]:
    """Generate a single-space dashboard: relative Markdown links work without GitBook IDs."""
    local = config['local']
    local_pages = sorted(NOTES.glob(local['chapter_glob']))
    if not local_pages or local_pages[0].name != local['entry']:
        raise ValueError('Local course entry must be the first existing chapter')
    summary = ['# Summary', '', '* [Dashboard](README.md)',
               f'* [{local["title"]}]({local["entry"]})']
    for path in local_pages[1:]:
        summary.append(f'  * [{title(path)}]({path.name})')
    cards = [(local['title'], local['description'], local['entry'])]
    output = {}
    for course in config['imports']:
        manifest = manifest_for(course)
        if (manifest['repository'], manifest['branch']) != (course['repository'], course['branch']):
            raise ValueError('Source settings changed; refresh before generating navigation')
        folder = destination(course)
        entry = (folder / 'README.md').relative_to(NOTES).as_posix()
        cards.append((course['title'], course['description'], entry))
        summary.append(f'* [{course["title"]}]({entry})')
        base = f'https://github.com/{manifest["repository"]}'
        sha = manifest['commit']
        overview = [f'# {course["title"]}', '', '[← All courses](../../README.md)', '',
                    course['description'], '',
                    f'**{len(manifest["files"])} available chapters**, published from '
                    f'[{manifest["repository"]}]({base}/tree/{sha}) '
                    f'— branch `{manifest["branch"]}`, revision [`{sha[:7]}`]({base}/commit/{sha}).', '',
                    'Read the notes here in GitBook. For runnable project setup and source files, use the original repository.', '',
                    '**Publication copy:** this course is refreshed from its source repository; upstream changes '
                    'are not automatically imported by GitBook. The source README also lists chapters that are not '
                    'present in this revision. Only files that actually exist are included below.', '']
        group = None
        for name in sorted(manifest['files']):
            current = name.split('/')[0]
            group_title = course.get('group_titles', {}).get(current, current.replace('-', ' '))
            if current != group:
                overview.extend(['', f'## {group_title}', ''])
                group = current
            page_title = title(folder / name)
            overview.append(f'- [{page_title}]({name})')
            published_path = (folder / name).relative_to(NOTES).as_posix()
            summary.append(f'  * [{group_title} · {page_title}]({published_path})')
        if manifest['unavailable_links']:
            overview.extend(['', '## References to future material', '',
                             'Some source chapters refer to files absent from this branch. Those links are displayed '
                             'as “not available in this published source revision” instead of sending you to a 404. '
                             'Code examples are left unchanged.'])
        output[folder / 'README.md'] = '\n'.join(overview) + '\n'
    dashboard = [f'# {config["site_title"]}', '', '## Choose your learning path', '',
                 'Pick a course below to read its notes, examples and exercises. Each course opens here in GitBook.', '',
                 '<table data-view="cards"><thead><tr><th></th><th></th>'
                 '<th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody>']
    for heading, description, target in cards:
        dashboard.append(f'<tr><td><strong>{html.escape(heading)}</strong></td><td>{html.escape(description)}</td>'
                         f'<td><a href="{html.escape(target, quote=True)}">Open course</a></td></tr>')
    dashboard.extend(['</tbody></table>', '', '### Quick links', ''])
    dashboard.extend(f'- [{heading}]({target})' for heading, _, target in cards)
    dashboard.extend(['', '### How to use this library', '',
                      'Start with a course overview, then follow its chapters in the sidebar. Each course stays '
                      'grouped together. Choose **Dashboard** in the sidebar whenever you want to switch courses.', '',
                      'Python/FastAPI is maintained in this documentation repository. Other repositories are '
                      'published here as attributed, revision-tracked documentation copies; their original '
                      'repositories remain the source of truth.'])
    output[NOTES / 'README.md'] = '\n'.join(dashboard) + '\n'
    output[NOTES / 'SUMMARY.md'] = '\n'.join(summary) + '\n'
    return output


def check(config: dict) -> None:
    for path, expected in render(config).items():
        if not path.exists() or path.read_text() != expected:
            raise ValueError(f'{path.relative_to(ROOT)} is stale; run python tools/sync_gitbook.py')
    for course in config['imports']:
        assert_unedited(course)
    summary = (NOTES / 'SUMMARY.md').read_text()
    entries = re.findall(r'^\s*\* \[[^\]]+\]\(([^)]+)\)$', summary, re.M)
    if len(entries) != len(set(entries)):
        raise ValueError('Duplicate pages in the GitBook sidebar')
    for entry in entries:
        page = (NOTES / entry).resolve()
        if not page.is_relative_to(NOTES) or not page.is_file():
            raise ValueError(f'Missing/out-of-scope sidebar page: {entry}')
        chunks = []
        prose_map(page.read_text(), lambda value: chunks.append(value) or value)
        visible = re.sub(r'`+[^`\n]*`+', '', ''.join(chunks))
        hrefs = re.findall(r'!?\[[^\]\n]*\]\(([^\s)]+)\)', visible)
        hrefs += re.findall(r'(?:href|src)=["\']([^"\']+)["\']', visible)
        for href in hrefs:
            target = local_target(entry, href)
            if target is not None:
                resolved = (NOTES / target).resolve()
                if not resolved.is_relative_to(NOTES) or not resolved.is_file():
                    raise ValueError(f'{entry}: broken/out-of-scope link {href}')
    print(f'GitBook dashboard verified: {1 + len(config["imports"])} courses, {len(entries)} unique pages; '
          'local/card links and imported-file hashes valid.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--refresh', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    config = json.loads((ROOT / 'gitbook-sources.json').read_text())
    ids = [course['id'] for course in config['imports']]
    if len(ids) != len(set(ids)):
        raise ValueError('Imported course IDs must be unique')
    if args.check:
        check(config)
        return
    if args.refresh:
        for course in config['imports']:
            refresh(course)
    for path, content in render(config).items():
        path.write_text(content)
    check(config)


if __name__ == '__main__':
    main()
