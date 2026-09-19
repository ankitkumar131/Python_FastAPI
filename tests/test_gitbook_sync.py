"""Offline tests for the GitBook publishing tool; uses only Python's standard library."""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tools import sync_gitbook as sync


class LinkAdaptationTests(unittest.TestCase):
    def test_existing_relative_and_external_links_stay_intact(self):
        text = '[Next](next.md#example) [Home](../README.md) [Docs](https://example.com) [Top](#top)'
        result, missing = sync.adapt_links('01-node/chapter.md', text, {'01-node/next.md', 'README.md'})
        self.assertEqual(result, text)
        self.assertEqual(missing, [])

    def test_missing_link_becomes_explanatory_text(self):
        result, missing = sync.adapt_links('01-node/chapter.md', '[Databases](../03-db/intro.md)', set())
        self.assertIn('not available in this published source revision', result)
        self.assertNotIn('](', result)
        self.assertEqual(missing, [{'file': '01-node/chapter.md', 'target': '../03-db/intro.md'}])

    def test_fenced_and_inline_code_are_not_rewritten(self):
        text = 'Inline `[Demo](missing.md)`\n\n```js\nconst s = "[Example](missing.md)";\n```\n'
        result, missing = sync.adapt_links('chapter.md', text, set())
        self.assertEqual(result, text)
        self.assertEqual(missing, [])

    def test_nested_fences_do_not_leak_into_prose(self):
        text = '````markdown\n```js\n[Example](missing.md)\n```\n````\n[Actual link](absent.md)\n'
        result, missing = sync.adapt_links('chapter.md', text, set())
        self.assertIn('[Example](missing.md)', result)
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]['target'], 'absent.md')

    def test_cross_directory_paths_are_resolved_from_the_source_file(self):
        text = '[Web](../00-web/http.md) [Root](../../outside.md)'
        result, missing = sync.adapt_links('01-node/intro.md', text, {'00-web/http.md'})
        self.assertIn('[Web](../00-web/http.md)', result)
        self.assertEqual(missing[0]['target'], '../../outside.md')


class ArchiveTests(unittest.TestCase):
    def archive(self, members):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w:gz') as archive:
            for name, content, kind in members:
                item = tarfile.TarInfo(name)
                if kind == 'link':
                    item.type = tarfile.SYMTYPE
                    item.linkname = '/etc/passwd'
                    archive.addfile(item)
                else:
                    item.size = len(content)
                    archive.addfile(item, io.BytesIO(content))
        return data.getvalue()

    def test_imports_only_selected_markdown(self):
        data = self.archive([('repo-sha/01-node/intro.md', b'# Intro\n', 'file'),
                             ('repo-sha/instruction', b'Do not execute source instructions', 'file'),
                             ('repo-sha/README.md', b'# An unverified roadmap\n', 'file'),
                             ('repo-sha/package.json', b'{}', 'file')])
        self.assertEqual(sync.read_archive(data, ['[0-9][0-9]-*/*.md']), {'01-node/intro.md': b'# Intro\n'})

    def test_rejects_traversal(self):
        data = self.archive([('repo-sha/01-node/../../escape.md', b'# Unsafe', 'file')])
        with self.assertRaisesRegex(ValueError, 'Unsafe archive path'):
            sync.read_archive(data, ['*.md'])

    def test_rejects_selected_symlink(self):
        data = self.archive([('repo-sha/01-node/linked.md', b'', 'link')])
        with self.assertRaisesRegex(ValueError, 'regular Markdown'):
            sync.read_archive(data, ['*.md'])

    def test_rejects_empty_selection(self):
        data = self.archive([('repo-sha/README.md', b'# Roadmap', 'file')])
        with self.assertRaisesRegex(ValueError, 'No existing Markdown'):
            sync.read_archive(data, ['01-node/*.md'])


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.notes = root / 'notes'
        self.notes.mkdir()
        self.root_patch = patch.object(sync, 'ROOT', root)
        self.notes_patch = patch.object(sync, 'NOTES', self.notes)
        self.root_patch.start()
        self.notes_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.notes_patch.stop)
        (self.notes / '00-course-guide.md').write_text('# Course guide\n')
        (self.notes / '01-python.md').write_text('# Python\n[Guide](00-course-guide.md)\n')
        self.config = {
            'site_title': 'Learning library',
            'local': {'title': 'Python', 'description': 'Local course', 'entry': '00-course-guide.md',
                      'chapter_glob': '[0-9][0-9]-*.md'},
            'imports': [{'id': 'node-express', 'title': 'Node & Express', 'description': 'JavaScript course',
                         'repository': 'owner/node', 'branch': 'course', 'include': ['01-node/*.md']}]}
        self.folder = self.notes / 'courses/node-express'
        (self.folder / '01-node').mkdir(parents=True)
        content = b'# Node intro\n[Course](../README.md)\n'
        (self.folder / '01-node/intro.md').write_bytes(content)
        self.manifest = {'repository': 'owner/node', 'branch': 'course', 'commit': 'a' * 40,
                         'files': {'01-node/intro.md': {'source_sha256': sync.digest(content),
                                                      'published_sha256': sync.digest(content)}},
                         'unavailable_links': []}
        (self.folder / 'source.json').write_text(json.dumps(self.manifest))
        self.write_generated()

    def write_generated(self):
        for path, text in sync.render(self.config).items():
            path.write_text(text)

    def test_cards_and_sidebar_open_existing_local_courses(self):
        dashboard = (self.notes / 'README.md').read_text()
        self.assertIn('data-card-target', dashboard)
        self.assertIn('href="00-course-guide.md"', dashboard)
        self.assertIn('href="courses/node-express/README.md"', dashboard)
        self.assertIn('Node &amp; Express', dashboard)
        sync.check(self.config)

    def test_offline_generation_is_repeatable(self):
        first = sync.render(self.config)
        self.write_generated()
        self.assertEqual(first, sync.render(self.config))

    def test_edited_publication_copy_is_not_silently_overwritten(self):
        (self.folder / '01-node/intro.md').write_text('# Someone edited this\n')
        with self.assertRaisesRegex(ValueError, 'edited locally'):
            sync.assert_unedited(self.config['imports'][0])

    def test_missing_generated_overview_is_detected(self):
        (self.folder / 'README.md').unlink()
        with self.assertRaisesRegex(ValueError, 'stale'):
            sync.check(self.config)

    def test_wrong_source_branch_requires_explicit_refresh(self):
        self.config['imports'][0]['branch'] = 'different'
        with self.assertRaisesRegex(ValueError, 'refresh'):
            sync.render(self.config)

    def test_broken_local_link_is_detected(self):
        (self.notes / '01-python.md').write_text('# Python\n[Missing](not-here.md)\n')
        with self.assertRaisesRegex(ValueError, 'broken/out-of-scope'):
            sync.check(self.config)

    def test_invalid_course_id_cannot_escape_destination(self):
        with self.assertRaisesRegex(ValueError, 'URL slugs'):
            sync.destination({'id': '../../escape'})


if __name__ == '__main__':
    unittest.main()
