"""Offline tests for the publisher app: form validation, source preview and dry runs.

No network calls: the GitHub CLI is never used here. Archive-based tests build their own
tarball and patch the two functions that would talk to GitHub.
"""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from publisher import core
from tools import sync_gitbook as engine


def archive(members: dict[str, bytes]) -> bytes:
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w:gz') as tar:
        for name, content in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return data.getvalue()


class FormTests(unittest.TestCase):
    def test_repository_references_are_normalised(self):
        for reference in ['https://github.com/ankitkumar131/DSA-in-java',
                          'https://github.com/ankitkumar131/DSA-in-java/',
                          'git@github.com:ankitkumar131/DSA-in-java.git',
                          'https://github.com/ankitkumar131/DSA-in-java.git',
                          'ankitkumar131/DSA-in-java']:
            self.assertEqual(core.parse_repository(reference), 'ankitkumar131/DSA-in-java')

    def test_invalid_repository_is_rejected(self):
        for reference in ['', 'not a repo', 'https://gitlab.com/owner/repo']:
            with self.assertRaises(core.PublisherError):
                core.parse_repository(reference)

    def test_slug_and_id_validation(self):
        self.assertEqual(core.slugify('DSA in Java — 30 Days!'), 'dsa-in-java-30-days')
        course = core.course_from_form({'title': 'DSA in Java', 'repository': 'o/r', 'branch': 'main'})
        self.assertEqual(course['id'], 'dsa-in-java')
        with self.assertRaisesRegex(core.PublisherError, 'lowercase'):
            core.course_from_form({'title': 'React', 'id': 'React_Notes', 'repository': 'o/r', 'branch': 'main'})
        with self.assertRaisesRegex(core.PublisherError, 'branch'):
            core.course_from_form({'title': 'React', 'repository': 'o/r'})
        with self.assertRaisesRegex(core.PublisherError, 'name'):
            core.course_from_form({'repository': 'o/r', 'branch': 'main'})

    def test_notes_directory_becomes_include_patterns(self):
        self.assertEqual(core.include_patterns(''), ['*.md'])
        self.assertEqual(core.include_patterns('  /notes/  '), ['notes/*.md'])
        self.assertEqual(core.include_patterns('a\\b'), ['a/b/*.md'])
        with self.assertRaisesRegex(core.PublisherError, '\\.\\.'):
            core.include_patterns('../outside')

    def test_directory_patterns_select_nested_chapters(self):
        # fnmatch lets `*` cross `/`, so one pattern covers the whole notes tree.
        self.assertTrue(engine.fnmatch.fnmatchcase('notes/a/b/day-01.md', 'notes/*.md'))
        self.assertFalse(engine.fnmatch.fnmatchcase('other/a.md', 'notes/*.md'))

    def test_explicit_patterns_and_folder_labels_from_the_form(self):
        course = core.course_from_form({
            'title': 'Spring Boot', 'repository': 'o/r', 'branch': 'arena/x',
            'include': 'day-*.md\nprojects/*.md',
            'group_titles': '{"projects": "Projects"}',
            'description': '  Backend notes  ',
        })
        self.assertEqual(course['include'], ['day-*.md', 'projects/*.md'])
        self.assertEqual(course['group_titles'], {'projects': 'Projects'})
        self.assertEqual(course['description'], 'Backend notes')
        with self.assertRaisesRegex(core.PublisherError, 'JSON'):
            core.course_from_form({'title': 'X', 'repository': 'o/r', 'branch': 'main', 'group_titles': '{oops'})

    def test_upsert_keeps_position_and_reports_new_entries(self):
        config = {'imports': [{'id': 'a'}, {'id': 'b'}]}
        self.assertTrue(core.upsert_course(config, {'id': 'c'}))
        self.assertFalse(core.upsert_course(config, {'id': 'a', 'title': 'updated'}))
        self.assertEqual([course['id'] for course in config['imports']], ['a', 'b', 'c'])
        self.assertEqual(config['imports'][0]['title'], 'updated')


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        notes = root / 'notes'
        notes.mkdir()
        (notes / '00-guide.md').write_text('# Guide\n')
        self.patches = [patch.object(engine, 'ROOT', root), patch.object(engine, 'NOTES', notes)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        self.published = notes / 'courses' / 'existing' / 'day-01.md'
        self.published.parent.mkdir(parents=True)
        content = b'# Existing day 1\n'
        self.published.write_bytes(content)
        (self.published.parent / 'source.json').write_text(json.dumps({
            'repository': 'owner/existing', 'branch': 'main', 'commit': 'c' * 40,
            'files': {'day-01.md': {'source_sha256': engine.digest(content),
                                    'published_sha256': engine.digest(content)}},
            'unavailable_links': []}))
        self.config = {
            'site_title': 'Library',
            'local': {'title': 'Python', 'description': '', 'entry': '00-guide.md',
                      'chapter_glob': '00-*.md'},
            'imports': [{'id': 'existing', 'title': 'Existing', 'description': '',
                         'repository': 'owner/existing', 'branch': 'main', 'include': ['*.md']}],
        }
        self.course = core.course_from_form({'title': 'DSA in Java', 'id': 'dsa-in-java',
                                             'repository': 'owner/dsa', 'branch': 'main',
                                             'notes_dir': 'course'})
        self.data = archive({
            'repo-sha/course/day-01.md': b'# Day 1\n[Next](day-02.md)\n',
            'repo-sha/course/day-02.md': b'# Day 2\n[Missing](../outside.md)\n',
            'repo-sha/README.md': b'# Not selected\n',
        })

    def preview(self, data=None):
        with patch.object(core, 'resolve_commit', return_value='a' * 40), \
             patch.object(core, 'fetch_archive', return_value=data or self.data):
            return core.preview_course(self.course, self.config)

    def test_preview_reports_selected_chapters_without_writing(self):
        result = self.preview()
        self.assertEqual(result['commit'], 'a' * 40)
        self.assertEqual([page['source'] for page in result['pages']],
                         ['course/day-01.md', 'course/day-02.md'])
        self.assertEqual([page['title'] for page in result['pages']], ['Day 1', 'Day 2'])
        self.assertEqual(result['pages'][0]['page'], 'courses/dsa-in-java/course/day-01')
        self.assertEqual(result['unavailable'], 1)
        self.assertFalse((engine.NOTES / 'courses' / 'dsa-in-java').exists())

    def test_preview_flags_a_page_path_that_would_collide(self):
        data = archive({'repo-sha/course/day-01.md': b'# Day 1\n',
                        'repo-sha/course/day-01/README.md': b'# Day 1 details\n'})
        result = self.preview(data)
        self.assertTrue(any('same GitBook page' in warning for warning in result['warnings']), result['warnings'])

    def test_preview_warns_about_a_gitbook_reexport_of_that_course(self):
        # GitBook writes lower-cased, folder-nested copies back into notes/ next to the publication.
        shadow = engine.NOTES / 'dsa-in-java' / 'course' / 'day-01.md'
        shadow.parent.mkdir(parents=True)
        shadow.write_text('# GitBook copy of day 1\n')
        result = self.preview()
        self.assertTrue(any('re-exported copy' in warning for warning in result['warnings']), result['warnings'])
        self.assertIn('notes/dsa-in-java/', result['warnings'][0])

    def test_preview_does_not_warn_about_another_courses_pages(self):
        # Published pages of other courses are normal; only this course's shadow copies are noise.
        extra = engine.NOTES / 'courses' / 'dsa-in-java' / 'course' / 'day-01.md'
        extra.parent.mkdir(parents=True)
        extra.write_text('# Day 1, already published\n')
        self.assertEqual(self.preview()['warnings'], [])

    def test_preview_rejects_a_directory_without_markdown(self):
        with self.assertRaisesRegex(core.PublisherError, 'No Markdown chapters'):
            self.preview(archive({'repo-sha/src/Main.java': b'class Main {}'}))

    def test_preview_rejects_an_unsafe_archive(self):
        with self.assertRaisesRegex(ValueError, 'Unsafe archive path'):
            self.preview(archive({'repo-sha/../../escape.md': b'# Unsafe\n'}))


class DryRunTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        (root / 'notes').mkdir()
        (root / 'notes' / '00-guide.md').write_text('# Guide\n')
        self.config = {'site_title': 'Library', 'local': {'title': 'Python', 'description': '',
                                                          'entry': '00-guide.md', 'chapter_glob': '00-*.md'},
                       'imports': []}
        self.config_path = root / 'gitbook-sources.json'
        self.config_path.write_text(json.dumps(self.config))
        self.patches = [patch.object(engine, 'ROOT', root), patch.object(engine, 'NOTES', root / 'notes'),
                        patch.object(core, 'CONFIG_PATH', self.config_path)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        self.payload = {'title': 'New course', 'repository': 'owner/repo', 'branch': 'main',
                        'notes_dir': 'notes', 'options': {'dry_run': True}}

    def test_dry_run_writes_nothing_and_pushes_nothing(self):
        preview = {'chapters': 2, 'commit_short': 'abc1234', 'patterns': ['notes/*.md'],
                   'unavailable': 0, 'warnings': ['a warning'], 'commit': 'a' * 40}
        lines = []
        with patch.object(core, 'preview_course', return_value=preview), \
             patch.object(core, 'git', side_effect=AssertionError('git must not run in a dry run')):
            result = core.publish(self.payload, log=lambda level, message: lines.append((level, message)))
        self.assertTrue(result['dry_run'])
        self.assertFalse(result['published'])
        self.assertEqual(json.loads(self.config_path.read_text()), self.config)
        self.assertFalse((engine.NOTES / 'courses' / 'new-course').exists())
        self.assertIn(('warn', 'a warning'), lines)
        self.assertTrue(any(level == 'done' and 'Dry run' in message for level, message in lines))

    def test_publish_reports_a_missing_source_without_touching_git(self):
        failure = core.PublisherError('No Markdown chapters matched')
        with patch.object(core, 'preview_course', side_effect=failure), \
             patch.object(core, 'git', side_effect=AssertionError('git must not run')):
            with self.assertRaisesRegex(core.PublisherError, 'No Markdown chapters'):
                core.publish(self.payload, log=lambda level, message: None)


class AppTests(unittest.TestCase):
    """HTTP surface: state, validation errors and the token guard."""

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
        except ModuleNotFoundError as error:  # pragma: no cover - optional dependency
            raise unittest.SkipTest(f'FastAPI TestClient unavailable: {error}')
        from publisher import app as publisher_app
        cls.publisher_app = publisher_app
        cls.client = TestClient(publisher_app.app)

    def test_state_lists_courses_and_the_limits(self):
        response = self.client.get('/api/state')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn('courses', body)
        self.assertTrue(body['courses'])
        self.assertEqual(body['limits']['markdown_mb'], 25)
        self.assertTrue(any(course['id'] == 'dsa-in-java' for course in body['courses']))

    def test_index_page_loads_the_form(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        for element in ('Course name', 'Push to GitBook', 'Check source', 'Publish library'):
            self.assertIn(element, response.text)

    def test_preview_reports_form_errors_as_400(self):
        response = self.client.post('/api/preview', json={'title': '', 'repository': 'o/r', 'branch': 'main'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('name is required', response.json()['error'])

    def test_publish_and_remove_require_the_token_when_one_is_configured(self):
        original = self.publisher_app.TOKEN
        self.publisher_app.TOKEN = 'secret'
        try:
            self.assertEqual(self.client.post('/api/publish', json={}).status_code, 401)
            self.assertEqual(self.client.post('/api/remove', json={'id': 'x'}).status_code, 401)
            self.assertEqual(self.client.get('/api/state').status_code, 200)
        finally:
            self.publisher_app.TOKEN = original

    def test_unknown_job_is_reported(self):
        self.assertEqual(self.client.get('/api/jobs/does-not-exist').status_code, 404)


if __name__ == '__main__':
    unittest.main()
