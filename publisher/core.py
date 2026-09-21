"""Form-to-publication logic for the GitBook course publisher app.

This module owns everything the publisher app does that is *not* HTTP: turning a form
(repository, branch, notes directory, name, description) into a registry entry, previewing
what that entry would import without writing anything, and running the publication pipeline
(prune GitBook's re-export, refresh the course, regenerate the dashboard, commit, push).

The importer in `tools/sync_gitbook.py` remains the only code that reads or writes imported
chapters; this module drives it.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # allow `python publisher/app.py` as well as `python -m publisher.app`
    sys.path.insert(0, str(ROOT))

from tools import sync_gitbook as engine  # noqa: E402  (path set above)

CONFIG_PATH = ROOT / 'gitbook-sources.json'
ID_PATTERN = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
REPOSITORY_PATTERN = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+')
SHA_PATTERN = re.compile(r'[a-f0-9]{40}')
LOG_LEVELS = ('step', 'info', 'warn', 'error', 'done')


class PublisherError(Exception):
    """A problem the user can fix, reported in the app instead of a traceback."""


# --------------------------------------------------------------------------- validation

def parse_repository(reference: str) -> str:
    """Accept a clone URL, a browser URL or a bare `owner/repo` and return `owner/repo`."""
    value = (reference or '').strip().rstrip('/')
    if re.match(r'^(https?://|git@)', value, flags=re.IGNORECASE) and 'github.com' not in value.lower():
        raise PublisherError(f'Only GitHub repositories are supported — got {reference!r}')
    value = re.sub(r'^https?://(?:www\.)?github\.com/', '', value, flags=re.IGNORECASE)
    value = re.sub(r'^git@github\.com:', '', value)
    value = re.sub(r'\.git$', '', value)
    value = value.strip('/')
    parts = [part for part in value.split('/') if part]
    if len(parts) >= 2:
        value = f'{parts[-2]}/{parts[-1]}'
    if not REPOSITORY_PATTERN.fullmatch(value):
        raise PublisherError(
            f'Expected a GitHub repository such as https://github.com/owner/repo — got {reference!r}')
    return value


def slugify(name: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', (name or '').lower()).strip('-')
    return re.sub(r'-{2,}', '-', slug)


def include_patterns(notes_dir: str) -> list[str]:
    """Markdown selection patterns for a repository directory.

    Python's fnmatch treats `*` as matching `/` as well, so `<dir>/*.md` selects that
    directory and everything below it, which is what "the notes for this course" means.
    """
    directory = (notes_dir or '').strip().strip('/').replace('\\', '/')
    if directory in ('', '.'):
        return ['*.md']
    if '..' in directory.split('/'):
        raise PublisherError('The notes directory cannot contain ".."')
    return [f'{directory}/*.md']


def course_from_form(payload: dict) -> dict:
    """Build and validate a registry entry from app input."""
    title = (payload.get('title') or '').strip()
    if not title:
        raise PublisherError('A course name is required.')
    course_id = (payload.get('id') or '').strip() or slugify(title)
    if not ID_PATTERN.fullmatch(course_id):
        raise PublisherError(
            f'Course ID {course_id!r} must be lowercase letters, digits and single hyphens '
            '(for example "dsa-in-java").')
    branch = (payload.get('branch') or '').strip()
    if not branch:
        raise PublisherError('A source branch is required (for example "main").')
    patterns = payload.get('include') or include_patterns(payload.get('notes_dir') or '')
    if isinstance(patterns, str):
        patterns = [line.strip() for line in patterns.splitlines() if line.strip()]
    if not patterns:
        raise PublisherError('At least one Markdown include pattern is needed.')
    course = {
        'id': course_id,
        'title': title,
        'description': (payload.get('description') or '').strip(),
        'repository': parse_repository(payload.get('repository') or ''),
        'branch': branch,
        'include': patterns,
    }
    labels = payload.get('group_titles') or {}
    if isinstance(labels, str):
        try:
            labels = json.loads(labels or '{}')
        except json.JSONDecodeError as error:
            raise PublisherError(f'Folder labels must be JSON such as {{"dir": "Label"}}: {error}') from error
    if labels:
        if not isinstance(labels, dict) or not all(isinstance(v, str) for v in labels.values()):
            raise PublisherError('Folder labels must be a JSON object of text values.')
        course['group_titles'] = labels
    return course


# --------------------------------------------------------------------------- registry

def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + '\n')


def upsert_course(config: dict, course: dict) -> bool:
    """Insert or replace one registry entry, keeping its position. Returns True if new."""
    for index, existing in enumerate(config['imports']):
        if existing['id'] == course['id']:
            config['imports'][index] = course
            return False
    config['imports'].append(course)
    return True


def course_summaries(config: dict) -> list[dict]:
    rows = []
    for course in config['imports']:
        folder = engine.destination(course)
        manifest_path = folder / 'source.json'
        manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else None
        rows.append({
            'id': course['id'],
            'title': course['title'],
            'description': course.get('description', ''),
            'repository': course.get('repository', ''),
            'branch': course.get('branch', ''),
            'include': course.get('include', []),
            'imported': bool(manifest),
            'pages': len(manifest['files']) if manifest else 0,
            'commit': (manifest['commit'][:7] if manifest else ''),
        })
    return rows


# --------------------------------------------------------------------------- source access

def _gh(*args: str, timeout: int = 300) -> bytes:
    try:
        return subprocess.check_output(['gh', *args], cwd=ROOT, stderr=subprocess.STDOUT, timeout=timeout)
    except FileNotFoundError as error:
        raise PublisherError('The GitHub CLI (`gh`) is not installed or not on PATH.') from error
    except subprocess.CalledProcessError as error:
        detail = error.output.decode('utf-8', 'replace').strip().splitlines()
        raise PublisherError(f'gh {" ".join(args[:2])} failed: {detail[-1] if detail else error}') from error
    except subprocess.TimeoutExpired as error:
        raise PublisherError(f'gh {" ".join(args[:2])} timed out after {timeout}s') from error


def resolve_commit(repository: str, branch: str) -> str:
    payload = _gh('api', f'repos/{repository}/commits/{branch}', timeout=60)
    sha = json.loads(payload).get('sha', '')
    if not SHA_PATTERN.fullmatch(sha):
        raise PublisherError(f'GitHub did not return an immutable commit SHA for {repository}@{branch}')
    return sha


def fetch_archive(repository: str, sha: str) -> bytes:
    data = _gh('api', f'repos/{repository}/tarball/{sha}')
    if len(data) > 25_000_000:
        raise PublisherError('Source archive exceeds the 25 MB safety limit.')
    return data


def title_of(text: str, fallback: str) -> str:
    match = re.search(r'^#\s+(.+)$', text, re.M)
    return match.group(1).strip() if match else fallback


def preview_course(course: dict, config: dict, archive: bytes | None = None) -> dict:
    """Resolve the source branch, download it and report exactly what would be published."""
    sha = resolve_commit(course['repository'], course['branch'])
    data = archive if archive is not None else fetch_archive(course['repository'], sha)
    try:
        original = engine.read_archive(data, course['include'])
    except ValueError as error:
        if 'No existing Markdown' in str(error):
            raise PublisherError(
                f'No Markdown chapters matched {", ".join(course["include"])} in '
                f'{course["repository"]}@{course["branch"]}. Check the notes directory, the branch '
                'and the file extensions.') from error
        raise
    available = engine.publication_paths(set(original))
    pages, missing, warnings, seen = [], [], [], {}
    shadows = [path for path in engine.stray_pages(config)
               if path.relative_to(engine.NOTES).parts[:1] == (course['id'],)]
    if shadows:
        warnings.append(
            f'GitBook still has {len(shadows)} re-exported copy/copies under notes/{course["id"]}/ '
            '(paths like notes/dsa-in-java/…). They are removed before the import, so the push leaves '
            'one page per chapter.')
    for name, raw in original.items():
        text = raw.decode('utf-8')
        adapted, absent = engine.adapt_links(name, text, available)
        published = (Path('courses') / course['id'] / name).as_posix()
        page = engine.page_path(published)
        pages.append({
            'source': name,
            'page': page,
            'title': title_of(adapted, Path(name).stem.replace('-', ' ')),
            'unavailable': len(absent),
            'bytes': len(raw),
        })
        missing.extend(absent)
        if page in seen:
            warnings.append(f'“{name}” and “{seen[page]}” would become the same GitBook page ({page}).')
        seen[page] = name
    if not pages:
        raise PublisherError(
            f'No Markdown chapters matched {course["include"]} in {course["repository"]}@{course["branch"]}. '
            'Check the notes directory and branch.')
    return {
        'id': course['id'],
        'title': course['title'],
        'repository': course['repository'],
        'branch': course['branch'],
        'commit': sha,
        'commit_short': sha[:7],
        'patterns': course['include'],
        'chapters': len(pages),
        'pages': pages,
        'unavailable': len(missing),
        'unavailable_samples': [f'{item["file"]} → {item["target"]}' for item in missing[:10]],
        'warnings': warnings[:20],
        'bytes': sum(page['bytes'] for page in pages),
    }


# --------------------------------------------------------------------------- git

def git(*args: str, timeout: int = 300) -> str:
    try:
        return subprocess.check_output(['git', *args], cwd=ROOT,
                                       stderr=subprocess.STDOUT, timeout=timeout).decode('utf-8', 'replace')
    except FileNotFoundError as error:
        raise PublisherError('git is not installed or not on PATH.') from error
    except subprocess.CalledProcessError as error:
        detail = error.output.decode('utf-8', 'replace').strip()
        raise PublisherError(f'git {" ".join(args)} failed:\n{detail}') from error


def repository_state() -> dict:
    branch = git('rev-parse', '--abbrev-ref', 'HEAD').strip()
    try:
        remote = git('remote', 'get-url', 'origin').strip()
    except PublisherError:
        remote = ''
    return {'branch': branch, 'remote': remote, 'dirty': bool(git('status', '--porcelain').strip())}


def commit_and_push(branch: str, message: str, log) -> dict:
    """Stage the publication only, commit it and push it to `branch`."""
    branch = (branch or '').strip()
    if not branch:
        raise PublisherError('A publishing branch is required.')
    if git('status', '--porcelain', '--', 'notes', 'gitbook-sources.json').strip():
        git('add', '-A', '--', 'notes', 'gitbook-sources.json')
    staged = git('diff', '--cached', '--name-only').strip()
    if not staged:
        log('info', 'Nothing to commit: the publication already matches the registry.')
        return {'commit': '', 'pushed': False, 'files': 0}
    files = len(staged.splitlines())
    git('commit', '-m', message)
    commit = git('rev-parse', 'HEAD').strip()
    log('step', f'Committed {files} file(s) as {commit[:7]}')
    local = git('rev-parse', '--abbrev-ref', 'HEAD').strip()
    refspec = f'HEAD:refs/heads/{branch}' if local != branch else branch
    git('push', 'origin', refspec, timeout=600)
    log('done', f'Pushed {commit[:7]} to origin/{branch}')
    return {'commit': commit, 'pushed': True, 'files': files, 'branch': branch}


# --------------------------------------------------------------------------- pipeline

def publish(payload: dict, log=None) -> dict:
    """Run the whole publication: prune, import, regenerate, validate, commit, push."""
    log = log or (lambda level, message: None)
    options = payload.get('options') or {}
    dry_run = bool(options.get('dry_run'))
    branch = (options.get('branch') or '').strip()
    message = (options.get('message') or '').strip()
    config = load_config()
    if payload.get('mode') == 'library':
        log('step', 'Publishing the current library without importing a new course.')
        preview = None
        course = None
    else:
        course = course_from_form(payload)
        log('step', f'Checking {course["repository"]}@{course["branch"]} for “{course["title"]}”')
        preview = preview_course(course, config)
        log('info', f'Revision {preview["commit_short"]}: {preview["chapters"]} Markdown chapter(s) '
                    f'matched {", ".join(preview["patterns"])}')
        for warning in preview['warnings']:
            log('warn', warning)
        if preview['unavailable']:
            log('warn', f'{preview["unavailable"]} link(s) point outside the publication; they will be '
                         'marked "not available in this published source revision".')
        if dry_run:
            log('done', 'Dry run: nothing was written, committed or pushed.')
            return {'preview': preview, 'published': False, 'dry_run': True}

    pruned = 0
    for path in engine.stray_pages(config):
        log('info', f'Removing GitBook re-exported copy {path.relative_to(engine.ROOT)}')
        pruned += 1
    if pruned:
        engine.prune_reexport(config)

    if course is not None:
        engine.refresh(course)
        manifest = engine.manifest_for(course)
        log('step', f'Imported {len(manifest["files"])} chapter(s) from commit '
                    f'{manifest["commit"][:7]} ({manifest["repository"]})')
        created = upsert_course(config, course)
        log('info', f'Registry entry “{course["id"]}” {"added" if created else "updated"}.')
    engine.write_generated(config)
    log('step', 'Regenerated the dashboard and the sidebar from the registry.')
    save_config(config)
    engine.check(config)
    log('info', f'Validation passed: {len(config["imports"]) + 1} courses, '
                f'{len((engine.NOTES / "SUMMARY.md").read_text().splitlines())} navigation lines.')

    log('step', f'Committing to {branch or "the current branch"}')
    result = commit_and_push(branch, message or _default_message(payload), log)
    result.update({'preview': preview, 'published': result['pushed'], 'pruned': pruned})
    if not result['pushed']:
        log('warn', 'The publication was already up to date, so nothing was pushed.')
    return result


def _default_message(payload: dict) -> str:
    if payload.get('mode') == 'library':
        return 'Publish GitBook library from the publisher app'
    title = (payload.get('title') or payload.get('id') or 'course').strip()
    return f'Publish {title} to the GitBook library'


def capture(func, *args, **kwargs) -> tuple[str, object]:
    """Run `func`, returning (standard output, result) so the app can log engine output."""
    buffer = StringIO()
    with redirect_stdout(buffer):
        result = func(*args, **kwargs)
    return buffer.getvalue(), result
