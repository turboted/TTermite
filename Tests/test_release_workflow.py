import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


versioning = load('prepare_version', 'prepare-version.py')
release = load('release_assets', 'release-artifacts.py')


class ReleaseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ttermite-release-test-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.root = self.folder / 'repo'; self.root.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Release Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.write('.gitignore', '/build/\n')
        self.write('project.yml', 'MARKETING_VERSION: "1.0.0"\nCURRENT_PROJECT_VERSION: "1"\n')
        self.write('release-history.json', json.dumps({'releases': [{'version': '1.0.0', 'endRevision': None}]}))
        self.write('obsolete.txt', 'Original source survives in history.')
        self.commit('base')
        self.notes = dict(change={'id': 'fixture-change', 'category': 'improved'}, noteCategories=['improved'], titles={l: 'Specific change' for l in versioning.LANGUAGES},
                          notes={l: [f'[{versioning.policy.CATEGORIES["improved"][versioning.policy.LANGUAGES.index(l)]}] What changed and why'] for l in versioning.LANGUAGES})

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()

    def write(self, name, value):
        p = self.root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(value)

    def commit(self, message):
        self.git('add', '-A'); self.git('commit', '-qm', message)

    def test_prepare_preserves_code_and_creates_one_pending_record_without_committing(self):
        head = self.git('rev-parse', 'HEAD')
        self.write('Source.swift', '// a real pending change')
        self.assertEqual(versioning.prepare(self.root, self.notes, release_date='2026-10-26'), ('1.0.1', 2))
        data = json.loads((self.root / 'release-history.json').read_text())
        self.assertEqual(len(data['releases']), 2)
        self.assertEqual(data['releases'][0]['baseRevision'], head)
        self.assertEqual(data['releases'][1]['endRevision'], head)
        self.assertIsNone(data['releases'][0]['endRevision'])
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual((self.root / 'Source.swift').read_text(), '// a real pending change')
        with self.assertRaisesRegex(ValueError, 'already pending'):
            versioning.prepare(self.root, self.notes)

    def test_blank_or_malformed_notes_do_not_change_version_files(self):
        before = [(self.root / name).read_bytes() for name in ['project.yml', 'release-history.json']]
        for bad in [[], {}, dict(titles=[], notes={}), dict(titles=self.notes['titles'], notes={'en': []})]:
            with self.assertRaises(ValueError): versioning.prepare(self.root, bad)
        self.assertEqual(before, [(self.root / name).read_bytes() for name in ['project.yml', 'release-history.json']])

    def test_does_not_overwrite_edited_history_or_accept_old_versions(self):
        for value in ['0.9.0', '1.0.0', 'not-a-version']:
            with self.assertRaises(ValueError): versioning.prepare(self.root, self.notes, value)
        data = json.loads((self.root / 'release-history.json').read_text())
        data['userEdit'] = 'preserve'
        self.write('release-history.json', json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'local edits'): versioning.prepare(self.root, self.notes)
        self.assertEqual(json.loads((self.root / 'release-history.json').read_text())['userEdit'], 'preserve')

    def test_bundle_clones_full_history_and_excludes_ignored_and_deleted_files(self):
        original = self.git('rev-parse', 'HEAD')
        (self.root / 'obsolete.txt').unlink()
        self.write('README.md', '# Clean source')
        self.commit('remove obsolete current source')
        self.write('build/private.log', 'local-only test fixture')
        destination = self.folder / 'source.bundle'
        release.source_bundle(self.root, destination)
        clone = self.folder / 'cloned'
        subprocess.run(['git', 'clone', '-q', str(destination), str(clone)], check=True)
        self.assertEqual(subprocess.check_output(['git', '-C', str(clone), 'rev-parse', 'HEAD'], text=True).strip(), self.git('rev-parse', 'HEAD'))
        self.assertFalse((clone / 'build').exists())
        self.assertFalse((clone / 'obsolete.txt').exists())
        self.assertEqual(subprocess.check_output(['git', '-C', str(clone), 'show', f'{original}:obsolete.txt'], text=True), 'Original source survives in history.')

    def test_bundle_also_clones_a_detached_release_revision(self):
        self.git('checkout', '-q', '--detach')
        destination = self.folder / 'detached.bundle'
        release.source_bundle(self.root, destination)
        clone = self.folder / 'detached-clone'
        subprocess.run(['git', 'clone', '-q', str(destination), str(clone)], check=True)
        self.assertTrue((clone / 'project.yml').is_file())

    def test_packaging_rejects_dirty_repository(self):
        self.write('uncommitted.txt', 'not reviewed')
        with self.assertRaisesRegex(ValueError, 'Commit all'):
            release.clean_revision(self.root)

    def test_history_validation_rejects_wrong_binary_and_combined_release_records(self):
        revision = 'a' * 40
        history = dict(version='1.0.0', build='1', revision=revision, dirty=False,
                       releases=[dict(version='1.0.0', commitIDs=[revision])], commits=[dict(id=revision)])
        release.validate_history(history, revision, '1.0.0', '1')
        for field, value in [('version', '0.0.0'), ('revision', 'b'*40), ('dirty', True)]:
            broken = dict(history); broken[field] = value
            with self.assertRaises(ValueError): release.validate_history(broken, revision, '1.0.0', '1')
        history['releases'][0]['commitIDs'].append('b'*40)
        with self.assertRaises(ValueError): release.validate_history(history, revision, '1.0.0', '1')


if __name__ == '__main__':
    unittest.main()
