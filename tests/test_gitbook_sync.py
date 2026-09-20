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

    def test_folder_links_open_readmes_with_or_without_trailing_slash(self):
        text = '[Day 1](practical/day-01) [Day 2](practical/day-02/)'
        result, missing = sync.adapt_links('INDEX.md', text,
            {'practical/day-01/README.md', 'practical/day-02/README.md'})
        self.assertEqual(result, '[Day 1](practical/day-01/README.md) [Day 2](practical/day-02/README.md)')
        self.assertEqual(missing, [])

    def test_nested_folder_links_preserve_query_fragment_and_inline_label(self):
        result, missing = sync.adapt_links('course/lesson.md',
            '[`lab`](../practical/day-01/?view=full#run)', {'practical/day-01/README.md'})
        self.assertEqual(result, '[`lab`](../practical/day-01/README.md?view=full#run)')
        self.assertEqual(missing, [])

    def test_generated_folder_indexes_are_valid_targets_but_absent_folders_are_not(self):
        available = sync.publication_paths({'course/part/chapter.md'})
        self.assertEqual(available, {'README.md', 'course/README.md',
                                    'course/part/README.md', 'course/part/chapter.md'})
        result, missing = sync.adapt_links('course/start.md',
            '[Part](part/) [Examples](../src/)', available)
        self.assertIn('[Part](part/README.md)', result)
        self.assertEqual(missing, [{'file': 'course/start.md', 'target': '../src/'}])

    def test_folder_link_examples_inside_code_are_not_rewritten(self):
        text = 'Inline `[Lab](lab)`\n\n```md\n[Lab](lab)\n```\n[Lab](lab)\n'
        result, missing = sync.adapt_links('index.md', text, {'lab/README.md'})
        self.assertEqual(result, text.replace('```\n[Lab](lab)\n', '```\n[Lab](lab/README.md)\n'))
        self.assertEqual(missing, [])

    def test_missing_link_becomes_explanatory_text(self):
        result, missing = sync.adapt_links('01-node/chapter.md', '[Databases](../03-db/intro.md)', set())
        self.assertIn('not available in this published source revision', result)
        self.assertNotIn('](', result)
        self.assertEqual(missing, [{'file': '01-node/chapter.md', 'target': '../03-db/intro.md'}])

    def test_missing_link_with_code_formatted_label_is_adapted(self):
        text = '[`../05-react-concepts/intro.md`](../05-react-concepts/intro.md)'
        result, missing = sync.adapt_links('react-notes/04-hooks/rules.md', text, set())
        self.assertIn('`../05-react-concepts/intro.md`', result)
        self.assertIn('not available in this published source revision', result)
        self.assertNotIn('](', result)
        self.assertEqual(missing, [{'file': 'react-notes/04-hooks/rules.md',
                                    'target': '../05-react-concepts/intro.md'}])

    def test_existing_link_with_code_formatted_label_is_preserved(self):
        text = '[`next.md`](next.md#example)'
        result, missing = sync.adapt_links('react-notes/01-basics/start.md', text,
                                          {'react-notes/01-basics/next.md'})
        self.assertEqual(result, text)
        self.assertEqual(missing, [])

    def test_literal_inline_link_and_real_code_label_are_distinguished(self):
        text = 'Literal `[Demo](absent.md)`, followed by [`missing.md`](missing.md).'
        result, missing = sync.adapt_links('chapter.md', text, set())
        self.assertIn('`[Demo](absent.md)`', result)
        self.assertNotIn('[`missing.md`](missing.md)', result)
        self.assertEqual(missing, [{'file': 'chapter.md', 'target': 'missing.md'}])

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
        sync.write_generated(self.config)

    def add_source_page(self, name, text):
        path = self.folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = text.encode('utf-8')
        path.write_bytes(data)
        self.manifest['files'][name] = {'source_sha256': sync.digest(data),
                                        'published_sha256': sync.digest(data)}
        (self.folder / 'source.json').write_text(json.dumps(self.manifest))

    def test_nested_folders_and_root_files_have_the_correct_depth_and_order(self):
        self.add_source_page('react-notes/02-typescript/02-types.md', '# Types\n')
        self.add_source_page('react-notes/01-prerequisites/01-html.md', '# HTML\n')
        self.add_source_page('react-notes/02-typescript/01-start.md', '# Start\n')
        self.add_source_page('react-notes/common-errors.md', '# Common errors\n')
        self.add_source_page('quick-reference.md', '# Quick reference\n')
        before = (self.folder / 'source.json').read_bytes()
        self.write_generated()
        summary = (self.notes / 'SUMMARY.md').read_text()
        expected = [
            '  * [react-notes](courses/node-express/react-notes/README.md)',
            '    * [01-prerequisites](courses/node-express/react-notes/01-prerequisites/README.md)',
            '      * [HTML](courses/node-express/react-notes/01-prerequisites/01-html.md)',
            '    * [02-typescript](courses/node-express/react-notes/02-typescript/README.md)',
            '      * [Start](courses/node-express/react-notes/02-typescript/01-start.md)',
            '      * [Types](courses/node-express/react-notes/02-typescript/02-types.md)',
            '    * [Common errors](courses/node-express/react-notes/common-errors.md)',
        ]
        self.assertIn('\n'.join(expected), summary)
        self.assertIn('  * [Quick reference](courses/node-express/quick-reference.md)', summary)
        index = (self.folder / 'react-notes/02-typescript/README.md').read_text()
        self.assertIn('[← react-notes](../README.md)', index)
        self.assertIn('[Start](01-start.md)', index)
        self.assertIn('  - [01-prerequisites](react-notes/01-prerequisites/README.md)',
                      (self.folder / 'README.md').read_text())
        self.assertEqual(before, (self.folder / 'source.json').read_bytes())
        sync.check(self.config)

    def test_directory_label_overrides_use_full_source_relative_paths(self):
        self.add_source_page('one/shared/deep/chapter.md', '# One\n')
        self.add_source_page('two/shared/chapter.md', '# Two\n')
        self.config['imports'][0]['group_titles'] = {'one/shared': 'Custom name'}
        self.write_generated()
        summary = (self.notes / 'SUMMARY.md').read_text()
        self.assertIn('    * [Custom name](courses/node-express/one/shared/README.md)', summary)
        self.assertIn('    * [shared](courses/node-express/two/shared/README.md)', summary)
        self.assertIn('        * [One](courses/node-express/one/shared/deep/chapter.md)', summary)
        sync.check(self.config)

    def test_imported_directory_readme_is_reused_once_without_modification(self):
        self.add_source_page('01-node/README.md', '# Original folder introduction\n')
        data = (self.folder / '01-node/README.md').read_bytes()
        self.write_generated()
        self.assertEqual(data, (self.folder / '01-node/README.md').read_bytes())
        summary = (self.notes / 'SUMMARY.md').read_text()
        self.assertEqual(summary.count('(courses/node-express/01-node/README.md)'), 1)
        self.assertIn('    * [Node intro](courses/node-express/01-node/intro.md)', summary)
        sync.check(self.config)

    def test_source_cannot_replace_reserved_course_overview(self):
        self.add_source_page('README.md', '# Source root overview\n')
        with self.assertRaisesRegex(ValueError, 'reserved'):
            self.write_generated()
        self.assertEqual((self.folder / 'README.md').read_text(), '# Source root overview\n')

    def test_unmanaged_folder_readme_is_not_overwritten(self):
        path = self.folder / '01-node/README.md'
        path.write_text('# My manual index\n')
        with self.assertRaisesRegex(ValueError, 'unmanaged folder README'):
            self.write_generated()
        self.assertEqual(path.read_text(), '# My manual index\n')

    def test_dangling_folder_index_symlink_is_not_followed(self):
        path = self.folder / '01-node/README.md'
        path.unlink()
        target = self.folder / 'do-not-create.md'
        try:
            path.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Symlink creation is not available: {exc}")
        with self.assertRaisesRegex(ValueError, 'unmanaged folder README'):
            self.write_generated()
        self.assertFalse(target.exists())

    def test_stale_generated_folder_indexes_are_removed_but_unmanaged_files_remain(self):
        self.add_source_page('retired/nested/chapter.md', '# Retired\n')
        self.write_generated()
        (self.folder / 'retired/nested/chapter.md').unlink()
        del self.manifest['files']['retired/nested/chapter.md']
        (self.folder / 'source.json').write_text(json.dumps(self.manifest))
        unrelated = self.folder / 'retired/personal/README.md'
        unrelated.parent.mkdir()
        unrelated.write_text('# Personal notes\n')
        with self.assertRaisesRegex(ValueError, 'Stale folder indexes'):
            sync.check(self.config)
        self.write_generated()
        self.assertFalse((self.folder / 'retired/README.md').exists())
        self.assertFalse((self.folder / 'retired/nested/README.md').exists())
        self.assertEqual(unrelated.read_text(), '# Personal notes\n')
        sync.check(self.config)

    def test_missing_folder_index_is_detected(self):
        (self.folder / '01-node/README.md').unlink()
        with self.assertRaisesRegex(ValueError, 'stale'):
            sync.check(self.config)

    def test_spaces_in_directory_and_file_paths_are_encoded_in_navigation(self):
        self.add_source_page('extra notes/first lesson.md', '# First lesson\n')
        self.write_generated()
        summary = (self.notes / 'SUMMARY.md').read_text()
        self.assertIn('(courses/node-express/extra%20notes/README.md)', summary)
        self.assertIn('(courses/node-express/extra%20notes/first%20lesson.md)', summary)
        sync.check(self.config)

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
