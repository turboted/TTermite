import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/generate-app-history.py'
spec = importlib.util.spec_from_file_location('app_history_generator', SCRIPT)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class VersionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='ttermite-version-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Version Test')
        self.git('config', 'user.email', 'version@example.invalid')
        self.write('project.yml', 'MARKETING_VERSION: "0.1.0"\nCURRENT_PROJECT_VERSION: "1"\n')
        self.write('.gitignore', '/Berth/Resources/AppHistory.json\n')
        self.write('Berth/App.swift', '// base\n')
        self.commit('base')
        self.base = self.git('rev-parse', 'HEAD')

    def git(self, *args):
        return generator.git(self.root, *args)

    def write(self, path, text):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text)

    def commit(self, message):
        self.git('add', '.')
        self.git('commit', '-qm', message)

    def bump(self):
        self.write('project.yml', 'MARKETING_VERSION: "0.2.0"\nCURRENT_PROJECT_VERSION: "2"\n')

    def history(self):
        self.bump()
        notes = {lang: ['Release notes'] for lang in ['zh-Hant', 'zh-Hans', 'en']}
        self.write('release-history.json', json.dumps({'schemaVersion': 1, 'historyBaseRevision': self.base, 'releases': [
            {'version': '0.2.0', 'date': '2026-10-24', 'baseRevision': self.base,
             'endRevision': None, 'notes': notes}]}))
        self.write('upstream-baselines.json', json.dumps({'schemaVersion': 1, 'sources': [
            {'repository': 'xinghelee/Berth', 'revision': self.base, 'version': '1.9.14', 'branch': 'main'},
            {'repository': 'xinghelee/Termite', 'revision': 'f' * 40, 'version': '2.1.3', 'branch': 'main'}]}))

    def test_function_changes_require_both_version_and_build(self):
        self.write('Berth/App.swift', '// changed\n')
        with self.assertRaises(ValueError): generator.check_policy(self.root)
        self.write('project.yml', 'MARKETING_VERSION: "0.2.0"\nCURRENT_PROJECT_VERSION: "1"\n')
        with self.assertRaises(ValueError): generator.check_policy(self.root)
        self.bump()
        self.assertEqual(generator.check_policy(self.root), ('0.2.0', 2))

    def test_upstream_integration_requires_bump(self):
        self.write('upstream-baselines.json', '{}')
        with self.assertRaises(ValueError): generator.check_policy(self.root)
        self.bump()
        generator.check_policy(self.root)

    def test_documentation_tests_and_debug_harness_require_their_own_version(self):
        self.write('docs/note.md', 'documentation')
        self.write('BerthTests/Test.swift', '// test')
        self.write('Berth/Debug/Test.swift', '// harness')
        with self.assertRaises(ValueError): generator.check_policy(self.root)
        self.bump()
        self.assertEqual(generator.check_policy(self.root), ('0.2.0', 2))

    def test_committed_function_change_without_bump_is_rejected(self):
        self.write('Berth/App.swift', '// changed\n')
        self.commit('forgot version')
        with self.assertRaises(ValueError): generator.check_policy(self.root)
        self.bump()
        generator.check_policy(self.root)

    def test_documentation_commit_does_not_hide_forgotten_bump(self):
        self.write('Berth/中文 檔案.swift', '// changed\n')
        with self.assertRaises(ValueError): generator.check_policy(self.root)
        self.commit('forgot version')
        self.write('docs/note.md', 'later documentation')
        self.commit('docs: example')
        with self.assertRaises(ValueError): generator.check_policy(self.root)

    def test_generation_preserves_git_bodies_and_maps_versions(self):
        self.history()
        self.write('Berth/App.swift', '// feature\n')
        self.commit('feat: example\n\nOriginal body with 中文, spaces and #hash')
        payload = generator.generate(self.root)
        self.assertFalse(payload['dirty'])
        self.assertEqual(payload['commits'][0]['id'], self.git('rev-parse', 'HEAD'))
        self.assertIn('中文', payload['commits'][0]['body'])
        self.assertEqual(payload['releases'][0]['commitIDs'], [payload['revision']])
        self.assertTrue((self.root / 'Berth/Resources/AppHistory.json').exists())

    def test_stale_notes_missing_translation_and_bad_ranges_fail(self):
        self.history()
        path = self.root / 'release-history.json'
        original = json.loads(path.read_text())
        for mutation in ['version', 'language', 'range']:
            data = json.loads(json.dumps(original))
            release = data['releases'][0]
            if mutation == 'version': release['version'] = '0.1.0'
            if mutation == 'language': del release['notes']['zh-Hant']
            if mutation == 'range': release['baseRevision'] = 'f' * 40
            path.write_text(json.dumps(data))
            with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                generator.generate(self.root)

    def test_adopting_new_berth_preserves_history_without_requiring_upstream_object(self):
        self.history()
        baselines = self.root / 'upstream-baselines.json'
        data = json.loads(baselines.read_text())
        data['sources'][0]['revision'] = 'a' * 40
        data['sources'][0]['version'] = '1.10.0'
        baselines.write_text(json.dumps(data))
        self.write('Berth/App.swift', '// integrated change\n')
        self.commit('feat: integrate upstream')
        payload = generator.generate(self.root)
        self.assertEqual(payload['sources'][0]['version'], '1.10.0')
        self.assertEqual(payload['releases'][0]['commitIDs'], [payload['revision']])
        self.assertEqual(len(payload['commits']), 1)

    def test_combining_two_commits_in_one_version_is_rejected(self):
        self.history()
        self.write('Berth/App.swift', '// feature\n')
        self.commit('feat: example')
        self.write('docs/note.md', 'separate documentation')
        self.write('project.yml', 'MARKETING_VERSION: "0.2.1"\nCURRENT_PROJECT_VERSION: "3"\n')
        path = self.root / 'release-history.json'
        data = json.loads(path.read_text()); data['releases'][0]['version'] = '0.2.1'
        path.write_text(json.dumps(data))
        self.commit('docs: follow-up')
        with self.assertRaisesRegex(ValueError, 'ONE Git commit'):
            generator.generate(self.root)

    def test_individual_records_include_documentation_and_test_commits(self):
        self.history()
        self.write('Berth/App.swift', '// feature\n')
        self.commit('feat: example')
        first = self.git('rev-parse', 'HEAD')
        self.write('docs/note.md', 'separate documentation')
        self.write('project.yml', 'MARKETING_VERSION: "0.2.1"\nCURRENT_PROJECT_VERSION: "3"\n')
        path = self.root / 'release-history.json'
        data = json.loads(path.read_text()); old = data['releases'][0]
        old['endRevision'] = first
        data['releases'].insert(0, dict(version='0.2.1', date='2026-10-24',
            baseRevision=first, endRevision=None, notes=old['notes']))
        path.write_text(json.dumps(data))
        self.commit('docs: separate version')
        second = self.git('rev-parse', 'HEAD')
        self.write('BerthTests/Test.swift', '// verification')
        self.write('project.yml', 'MARKETING_VERSION: "0.2.2"\nCURRENT_PROJECT_VERSION: "4"\n')
        data['releases'][0]['endRevision'] = second
        data['releases'].insert(0, dict(version='0.2.2', date='2026-10-24',
            baseRevision=second, endRevision=None, notes=old['notes']))
        path.write_text(json.dumps(data))
        self.commit('test: separate version')
        payload = generator.generate(self.root)
        self.assertEqual([len(r['commitIDs']) for r in payload['releases']], [1, 1, 1])
        self.assertEqual(payload['releases'][1]['commitIDs'], [second])
        self.assertEqual(payload['releases'][2]['commitIDs'], [first])

    def test_retrospective_record_must_match_actual_original_version_and_timestamp(self):
        self.history()
        self.write('Berth/App.swift', '// feature\n')
        self.commit('feat: example')
        path = self.root / 'release-history.json'
        data = json.loads(path.read_text())
        release = data['releases'][0]
        release.update(retrospective=True, originalVersion='0.2.0',
            timestamp=self.git('show', '-s', '--format=%aI', 'HEAD'),
            titles={language: 'Specific title' for language in ('zh-Hant', 'zh-Hans', 'en')})
        release['date'] = release['timestamp'][:10]
        path.write_text(json.dumps(data))
        # Validation of historical metadata is independent of a pending new commit's bump.
        self.write('project.yml', 'MARKETING_VERSION: "0.2.1"\nCURRENT_PROJECT_VERSION: "3"\n')
        release['version'] = '0.2.1'
        path.write_text(json.dumps(data))
        generator.generate(self.root)
        for field, value in [('originalVersion', '0.0.9'), ('timestamp', '2020-01-01T00:00:00+08:00')]:
            broken = json.loads(json.dumps(data))
            broken['releases'][0][field] = value
            path.write_text(json.dumps(broken))
            with self.assertRaisesRegex(ValueError, 'actual commit'):
                generator.generate(self.root)


if __name__ == '__main__':
    unittest.main()
