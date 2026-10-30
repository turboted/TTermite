#!/usr/bin/env python3
"""Bundle verified local history and reject functional changes without a version bump."""
import json
import importlib.util
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
policy_spec = importlib.util.spec_from_file_location('version_policy', ROOT / 'scripts/version_policy.py')
policy = importlib.util.module_from_spec(policy_spec)
policy_spec.loader.exec_module(policy)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def version_settings(text):
    version = re.search(r'^\s*MARKETING_VERSION:\s*"(\d+\.\d+\.\d+)"', text, re.M)
    build = re.search(r'^\s*CURRENT_PROJECT_VERSION:\s*"(\d+)"', text, re.M)
    if not version or not build:
        raise ValueError('project.yml must declare a three-part version and numeric build.')
    return version.group(1), int(build.group(1))


def newer(current, previous):
    return tuple(map(int, current[0].split('.'))) > tuple(map(int, previous[0].split('.'))) and current[1] > previous[1]


def git_paths(root, *args):
    output = subprocess.check_output(['git', '-C', str(root), *args, '-z'])
    return output.decode('utf-8').split('\0')[:-1]


def check_policy(root):
    current = version_settings((root / 'project.yml').read_text())
    previous = version_settings(git(root, 'show', 'HEAD:project.yml'))
    changed = git_paths(root, 'diff', 'HEAD', '--name-only')
    changed += git_paths(root, 'ls-files', '--others', '--exclude-standard')
    if changed and not newer(current, previous):
        raise ValueError('Every new Git commit, including documentation and tests, requires increasing BOTH '
                         'MARKETING_VERSION and CURRENT_PROJECT_VERSION in project.yml, '
                         'and adding release notes to release-history.json.')
    latest = git(root, 'rev-parse', 'HEAD')
    if latest and len(git(root, 'rev-list', '--parents', '-n', '1', latest).split()) > 1:
        committed = version_settings(git(root, 'show', f'{latest}:project.yml'))
        parent = version_settings(git(root, 'show', f'{latest}^:project.yml'))
        if not newer(committed, parent) and not newer(current, previous):
            raise ValueError('The last Git commit did not increase the app version/build.')
    return current


def commit_records(root, start, end):
    output = subprocess.check_output(['git', '-C', str(root), 'log', '-z',
        '--format=%H%x00%aI%x00%s%x00%b', f'{start}..{end}' if start else end])
    fields = output.decode('utf-8', errors='replace').split('\0')
    if fields[-1] == '':
        fields.pop()
    if len(fields) % 4:
        raise ValueError('Unexpected Git history format')
    return [dict(zip(('id', 'date', 'subject', 'body'), fields[i:i + 4])) for i in range(0, len(fields), 4)]


def generate(root):
    version, build = check_policy(root)
    history = json.loads((root / 'release-history.json').read_text())
    baselines = json.loads((root / 'upstream-baselines.json').read_text())
    if history['schemaVersion'] != 1 or baselines['schemaVersion'] != 1:
        raise ValueError('Unsupported history or baseline schema')
    releases = history['releases']
    if history.get('versionPolicy') == 'single-change-v1':
        policy.validate_lineage(releases)
    if not releases or releases[0]['version'] != version:
        raise ValueError('The newest release-history.json entry must match MARKETING_VERSION')
    versions = [tuple(map(int, r['version'].split('.'))) for r in releases]
    if any(a <= b for a, b in zip(versions, versions[1:])):
        raise ValueError('Release versions must be unique and newest first')
    required = {'xinghelee/Berth', 'xinghelee/Termite'}
    if {s['repository'] for s in baselines['sources']} != required:
        raise ValueError('Both adopted upstream baselines must be present')
    for source in baselines['sources']:
        if not re.fullmatch('[0-9a-f]{40}', source['revision']) or not source['version']:
            raise ValueError('Each adopted version needs a full Git revision')
    head = git(root, 'rev-parse', 'HEAD')
    # The history origin is permanent; adopting a newer Berth revision must not truncate
    # earlier TTermite commits or require an upstream object after a selective port.
    origin = git(root, 'rev-parse', history['historyBaseRevision']) if history.get('historyBaseRevision') else None
    commits = commit_records(root, origin, head)
    available = {c['id'] for c in commits}
    assigned = set()
    expected_end = head
    for release in releases:
        end = release.get('endRevision') or head
        end = git(root, 'rev-parse', end)
        start = git(root, 'rev-parse', release['baseRevision']) if release.get('baseRevision') else None
        if end != expected_end:
            raise ValueError('Release ranges must be contiguous and end at the bundled revision')
        if start:
            subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', start, end], check=True)
        elif len(git(root, 'rev-list', '--parents', '-n', '1', end).split()) != 1:
            raise ValueError('Only a real root commit may have a null base.')
        for language in ('zh-Hant', 'zh-Hans', 'en'):
            if not release['notes'].get(language):
                raise ValueError('Release notes must include Traditional Chinese, Simplified Chinese and English')
        ids = [c['id'] for c in commit_records(root, start, end)]
        if len(ids) > 1:
            raise ValueError('Each version record must map to ONE Git commit; split combined history entries.')
        if not ids and release is not releases[0]:
            raise ValueError('Only the pending newest version may have no committed change yet.')
        if release.get('retrospective'):
            if not release.get('originalVersion') or not release.get('timestamp'):
                raise ValueError('Retrospective records must preserve the original app version and commit date.')
            if any(not release.get('titles', {}).get(language) for language in ('zh-Hant', 'zh-Hans', 'en')):
                raise ValueError('Retrospective records require individual titles in all three languages.')
            if ids:
                original = version_settings(git(root, 'show', f'{ids[0]}:project.yml'))[0]
                timestamp = git(root, 'show', '-s', '--format=%aI', ids[0])
                if original != release['originalVersion'] or timestamp != release['timestamp'] or timestamp[:10] != release['date']:
                    raise ValueError('Retrospective original version/date must match the actual commit.')
        if assigned.intersection(ids) or not set(ids).issubset(available):
            raise ValueError('Release commit mapping is overlapping or invalid')
        release['commitIDs'] = ids
        assigned.update(ids)
        expected_end = start
    if expected_end != origin or assigned != available:
        raise ValueError('Release ranges must cover all reachable TTermite commits since Berth')
    payload = dict(schemaVersion=1, version=version, build=str(build), revision=head,
                   branch=git(root, 'branch', '--show-current'),
                   dirty=bool(git(root, 'status', '--porcelain', '--untracked-files=normal')),
                   sources=baselines['sources'], releases=releases, commits=commits)
    destination = root / 'Berth/Resources/AppHistory.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
    if not destination.exists() or destination.read_text() != encoded:
        destination.write_text(encoded)
    return payload


if __name__ == '__main__':
    try:
        result = generate(ROOT)
        print(f"History: TTermite {result['version']} ({result['build']}), "
              f"{len(result['commits'])} commits, {result['revision'][:8]}" + (' + uncommitted changes' if result['dirty'] else ''))
    except (ValueError, subprocess.CalledProcessError, KeyError) as error:
        raise SystemExit(f'Version/history check failed: {error}')
