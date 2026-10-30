#!/usr/bin/env python3
"""Prepare exactly one pending version. Never commit, tag, push or infer release notes."""
import argparse
from datetime import date
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
policy_spec = importlib.util.spec_from_file_location('version_policy', ROOT / 'scripts/version_policy.py')
policy = importlib.util.module_from_spec(policy_spec)
policy_spec.loader.exec_module(policy)
spec = importlib.util.spec_from_file_location('app_history', ROOT / 'scripts/generate-app-history.py')
history_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history_module)
LANGUAGES = ('en', 'zh-Hans', 'zh-Hant')


def prepare(root, notes, version=None, release_date=None):
    if not isinstance(notes, dict):
        raise ValueError('Notes must be a JSON object with titles and notes.')
    if not isinstance(notes.get('titles'), dict) or not isinstance(notes.get('notes'), dict):
        raise ValueError('titles and notes must be JSON objects.')
    for language in LANGUAGES:
        title = notes.get('titles', {}).get(language)
        entries = notes.get('notes', {}).get(language)
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f'Fill in titles.{language}.')
        if not isinstance(entries, list) or not entries or any(not isinstance(n, str) or not n.strip() for n in entries):
            raise ValueError(f'Fill in notes.{language} with at least one nonempty string.')
    project = root / 'project.yml'
    release_file = root / 'release-history.json'
    if project.is_symlink() or release_file.is_symlink():
        raise ValueError('Version files must be regular files, not symlinks.')
    project_text = project.read_text()
    committed_project = history_module.git(root, 'show', 'HEAD:project.yml')
    old_version, old_build = history_module.version_settings(committed_project)
    if history_module.version_settings(project_text) != (old_version, old_build):
        raise ValueError('A version is already pending; edit its notes instead of incrementing again.')
    committed_history = json.loads(history_module.git(root, 'show', 'HEAD:release-history.json'))
    history = json.loads(release_file.read_text())
    if history != committed_history:
        raise ValueError('Release history already has local edits; preserve and review them first.')
    if history['releases'][0]['version'] != old_version:
        raise ValueError('The committed app version and newest history record differ.')
    change = policy.validate_change(notes.get('change'))
    policy.validate_notes(notes)
    expected = policy.next_version(old_version, change)
    if version is not None and version != expected:
        raise ValueError(f'This change requires version {expected}, not {version}.')
    version = expected
    stamp = date.fromisoformat(release_date) if release_date else date.today()
    head = history_module.git(root, 'rev-parse', 'HEAD')
    history['releases'][0]['endRevision'] = head
    history['releases'].insert(0, dict(version=version, date=stamp.isoformat(), baseRevision=head, endRevision=None,
                                     change=change, noteCategories=notes['noteCategories'],
                                     titles={l: notes['titles'][l].strip() for l in LANGUAGES},
                                     notes={l: [n.strip() for n in notes['notes'][l]] for l in LANGUAGES}))
    project_text = re.sub(r'(MARKETING_VERSION:\s*)"\d+\.\d+\.\d+"', lambda m: m[1] + f'"{version}"', project_text, count=1)
    project_text = re.sub(r'(CURRENT_PROJECT_VERSION:\s*)"\d+"', lambda m: m[1] + f'"{old_build + 1}"', project_text, count=1)
    replacements = [(project, project_text), (release_file, json.dumps(history, ensure_ascii=False, indent=2) + '\n')]
    staged = []
    try:
        for target, text in replacements:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=root, prefix='.version-', delete=False) as temporary:
                temporary.write(text)
                staged.append((Path(temporary.name), target))
        for temporary, target in staged:
            temporary.replace(target)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)
    return version, old_build + 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notes', required=True, type=Path, help='Completed copy of docs/release-notes-template.json')
    parser.add_argument('--version', help='Optional explicit version; must match the category-based increment.')
    parser.add_argument('--date', help='Optional ISO release date; default is the local date.')
    args = parser.parse_args()
    try:
        version, build = prepare(ROOT, json.loads(args.notes.read_text()), args.version, args.date)
        print(f'Prepared {version}, build {build}. Review, test and commit your changes together; no commit, tag or push performed.')
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
