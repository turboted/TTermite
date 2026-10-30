#!/usr/bin/env python3
"""Read exact historical inputs. Preflight is never a successful build or privacy clearance."""
import argparse
import json
import importlib.util
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS='0')).strip()


def privacy_path(path):
    parts = path.lower().split('/')
    name = parts[-1]
    if set(parts) & {'.ssh', '.aws', '.gnupg', '.codex', '.mirasim', '.tgitsync', 'tgitsync-data', 'logs', '.logs', 'audit-logs', 'security-logs', 'operation-logs', 'verification', 'runtime', '.cache', '.local', '.build', 'node_modules', '__pycache__', 'xcuserdata'}:
        return 'local-record-or-cache'
    if name == '.env' or (name.startswith('.env.') and name.rsplit('.', 1)[-1] not in {'example', 'sample', 'template', 'dist'}):
        return 'private-environment'
    if name in {'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519', '.netrc', '.npmrc', '.pypirc', 'credentials', 'credentials.json', 'secrets.json', 'tokens.json', 'auth.json', '.gitconfig', '.bash_history', '.zsh_history', 'known_hosts'} or name.endswith(('.key', '.pem', '.p12', '.pfx', '.keystore', '.jks', '.keychain', '.keychain-db')):
        return 'credential-path'
    if name.endswith(('.log', '.trace', '.pid', '.sock', '.sqlite', '.sqlite3', '.db-wal', '.db-shm', '.xcuserstate', '.ax.txt', '.local.json', '.local.yml', '.local.yaml')) or name in {'.ds_store', 'state.db', 'history.db', 'sessions.db', 'security.db', 'operations.jsonl', 'audit.jsonl', 'security-events.jsonl'}:
        return 'local-state'
    if name.endswith('.json') and name.startswith(('creation-', 'management-', 'release-publication-', 'release-batch-', 'delivery-archive-', 'release-build-', 'pending-upload-', 'upload-history-', 'remote-status-', 'build-failure-')):
        return 'local-operation-record'
    return None


def source_findings(root, revision):
    # Inspect reachable historical names, not just the current index/ignore rules.
    records = git(root, 'rev-list', '--objects', revision).splitlines()
    findings = []
    for record in records:
        sha, _, path = record.partition(' ')
        reason = privacy_path(path) if path else None
        if reason:
            findings.append(dict(object=sha, path=path, reason=reason))
    return findings



def content_findings(root, revision):
    records = git(root, 'rev-list', '--objects', revision).splitlines()
    paths = dict(record.split(' ', 1) for record in records if ' ' in record)
    pattern = re.compile(rb'-----BEGIN ((?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY)-----[ \t]*[\r\n]+(?:[A-Za-z0-9+/=]{16,}[ \t]*[\r\n]+)+-----END \1-----|github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}')
    examples = {b'ghp_abcdefghijklmnopqrstuvwxyz0123456789ABCD', b'AKIAIOSFODNN7EXAMPLE'}
    found = []
    process = subprocess.Popen(['git', '-C', str(root), 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for sha, path in paths.items():
            process.stdin.write((sha + '\n').encode()); process.stdin.flush()
            header = process.stdout.readline().split()
            if len(header) != 3: raise ValueError('Invalid Git object response.')
            size = int(header[2]); payload = process.stdout.read(size)
            if process.stdout.read(1) != b'\n': raise ValueError('Incomplete Git object response.')
            if header[1] == b'blob' and any(m.group() not in examples for m in pattern.finditer(payload)):
                found.append(dict(object=sha, path=path, reason='credential-shaped-content-requires-review'))
    finally:
        process.stdin.close(); process.wait()
    return found


def require_source_publishable(root, revision):
    findings = source_findings(root, revision) + content_findings(root, revision)
    if findings:
        raise ValueError('Source publication blocked: reachable Git history contains local records/state. '
                         'Run python3 scripts/audit-release-support.py; removing current files cannot clean ancestors. '
                         'No Git history has been rewritten. Local app building is a separate step.')


def catalog(root):
    head = git(root, 'rev-parse', 'HEAD')
    data = json.loads(git(root, 'show', head + ':release-history.json'))
    vintage_spec = importlib.util.spec_from_file_location('vintage', ROOT / 'scripts/vintage-release-recipes.py')
    vintage = importlib.util.module_from_spec(vintage_spec); vintage_spec.loader.exec_module(vintage)
    rows = []
    for release in data['releases']:
        sha = release.get('endRevision') or head
        sha = git(root, 'rev-parse', sha)
        files = set(git(root, 'ls-tree', '-r', '--name-only', sha).splitlines())
        project = git(root, 'show', sha + ':project.yml')
        def value(key):
            return re.search(key + r':\s*"([^"]+)"', project)[1]
        if 'tgitsync-release.json' in files:
            test_command = ''
            command = 'python3 "$TGITSYNC_RELEASE_KIT/bin/release.py" run --manifest tgitsync-release.json'
            included = True
            inputs = ['tgitsync-release.json', 'scripts/release-app.py', 'scripts/support/PreferencesProfile.m',
                      'scripts/generate-app-history.py', 'scripts/check-release-app.py', 'scripts/test-core.sh',
                      'scripts/check-localizations.py', 'scripts/generate-component-catalog.py',
                      'project.yml', 'Package.resolved', 'license-audit.json', 'upstream-baselines.json']
            if 'dependency-sources.json' in files:
                inputs += ['dependency-sources.json', 'scripts/release_dependencies.py']
        elif 'scripts/release-app.py' in files:
            test_command, command, included = '', 'python3 scripts/release-app.py', True
            inputs = ['scripts/release-app.py', 'scripts/generate-app-history.py', 'project.yml', 'Package.resolved']
        elif 'scripts/build-release-app.sh' in files:
            test_command, command, included = '', 'bash scripts/build-release-app.sh', True
            inputs = ['scripts/test-release.sh', 'scripts/build-app.sh', 'scripts/package-app.sh', 'scripts/check-release-app.py', 'scripts/audit-release-support.py', 'scripts/test-core.sh', 'scripts/check-localizations.py', 'scripts/generate-app-history.py', 'scripts/generate-component-catalog.py', 'license-audit.json', 'upstream-baselines.json', 'Package.resolved']
        else:
            core = git(root, 'show', sha + ':scripts/test-core.sh') if 'scripts/test-core.sh' in files else ''
            test_command, command = vintage.recipe(files, core)
            included = False
            inputs = ['project.yml', 'Package.resolved', 'Berth/App/BerthApp.swift']
        missing = [name for name in inputs if name not in files]
        rows.append(dict(version=release['version'], revision=sha,
                         originalVersion=value('MARKETING_VERSION'), build=value('CURRENT_PROJECT_VERSION'),
                         retrospective=release.get('retrospective', False),
                         testCommand=test_command, buildCommand=command, testsIncludedInBuild=included, appPath='build/TTermite.app',
                         missingInputs=missing, candidateRecipeOnly=True, historyRequired='scripts/generate-app-history.py' in files, isolatedBuild='not-run',
                         githubPublication='not-verified',
                         currentPrivacyPaths=sorted(p for p in files if privacy_path(p)),
                         ancestralPrivacyFindingCount=len(source_findings(root, sha))))
    return dict(catalogRevision=head, versions=rows, sourceHistoryFindings=source_findings(root, head), contentFindings=content_findings(root, head),
                scope='Input, historical-path and common credential-format preflight only; not exhaustive privacy clearance, a build result, or a GitHub receipt.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/verification/release-support.json')
    parser.add_argument('--require-publishable', action='store_true', help='Fail on known historical privacy findings; not exhaustive clearance.')
    args = parser.parse_args()
    result = catalog(ROOT)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f"{len(result['versions'])} exact version inputs inspected; {len(result['sourceHistoryFindings'])} historical path findings.")
    print('No tests/builds, source edits, tags or uploads performed. Local report:', args.output)
    if args.require_publishable:
        try: require_source_publishable(ROOT, result['catalogRevision'])
        except ValueError as error: raise SystemExit(str(error))
