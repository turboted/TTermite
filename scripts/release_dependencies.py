"""Materialize the reviewed public dependency snapshots into one private build copy.

This is the manual's vendored-source route, not an extension of Kit's public
download cache. No Git objects, checkout, HOME or products are shared at runtime.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BARE_CONFIG = b'[core]\n\trepositoryformatversion = 0\n\tbare = true\n'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def configure(source, inventory_root=None, environment=None):
    source = Path(source).resolve()
    inventory_root = Path(inventory_root or source).resolve()
    env = dict(os.environ if environment is None else environment)
    lock_bytes = (source / 'Package.resolved').read_bytes()
    inventory = json.loads((inventory_root / 'dependency-sources.json').read_text())
    pins = {p['identity']: p for p in json.loads(lock_bytes)['pins']}
    packages = inventory['packages']
    if (inventory.get('schemaVersion') != 1 or inventory.get('lockSHA256') != digest(lock_bytes)
            or len(packages) != len(pins) or {p['identity'] for p in packages} != set(pins)):
        raise ValueError('Vendored dependency inventory must match the complete committed lockfile.')
    base = source / '.build/locked-package-sources'
    if base.is_symlink():
        raise ValueError('Dependency destination must be private to this source copy.')
    base.mkdir(parents=True, exist_ok=True)
    hooks = base / 'empty-hooks'
    hooks.mkdir(exist_ok=True)
    if any(hooks.iterdir()):
        raise ValueError('Dependency hooks directory must stay empty.')
    config = [('credential.helper', ''), ('core.hooksPath', str(hooks))]
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_TERMINAL_PROMPT='0',
               GIT_ALLOW_PROTOCOL='file')
    for package in packages:
        identity = package['identity']
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', identity):
            raise ValueError('Invalid dependency identity.')
        pin = pins[identity]
        if (package['sourceURL'] != pin['location'] or package['revision'] != pin['state']['revision']
                or package['version'] != pin['state']['version']):
            raise ValueError('Vendored dependency differs from its original locked source.')
        relative = PurePosixPath(package['archive'])
        if relative.is_absolute() or '..' in relative.parts or '\\' in str(relative):
            raise ValueError('Invalid dependency archive path.')
        archive = inventory_root / str(relative)
        if archive.is_symlink() or not archive.resolve().is_relative_to(inventory_root):
            raise ValueError('Dependency archive escapes the committed inventory.')
        data = archive.read_bytes()
        if len(data) != package['bytes'] or digest(data) != package['sha256']:
            raise ValueError('Vendored dependency archive SHA-256 mismatch.')
        destination = base / identity
        if destination.is_symlink():
            raise ValueError('Dependency repository must not be a symlink.')
        destination.mkdir(exist_ok=True)
        expected_files = set()
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist()
            if len(members) > 10000 or sum(m.file_size for m in members) > 512 * 1024 * 1024:
                raise ValueError('Dependency snapshot exceeds extraction limits.')
            for item in members:
                name = item.filename
                path = PurePosixPath(name)
                if (not name or path.is_absolute() or any(p in ('', '.', '..') for p in name.split('/'))
                        or '\\' in name or stat.S_ISLNK(item.external_attr >> 16) or item.flag_bits & 1
                        or item.is_dir() or name in expected_files):
                    raise ValueError('Unsafe dependency snapshot member.')
                expected_files.add(name)
                target = destination / name
                if target.is_symlink() or not target.parent.resolve().is_relative_to(destination.resolve()):
                    raise ValueError('Dependency snapshot destination escapes its copy.')
                payload = bundle.read(item)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    if not target.is_file() or digest(target.read_bytes()) != digest(payload):
                        raise ValueError('Materialized dependency was modified; use a new build copy.')
                else:
                    target.write_bytes(payload)
        actual_files = {str(p.relative_to(destination)) for p in destination.rglob('*') if p.is_file()}
        if actual_files != expected_files or (destination / 'config').read_bytes() != BARE_CONFIG:
            raise ValueError('Dependency repository contains unexpected files/configuration.')
        if (destination / 'shallow').read_text() != package['revision'] + '\n':
            raise ValueError('Dependency snapshot boundary mismatch.')
        verify_env = dict(env)
        verify_env.update(GIT_CONFIG_COUNT='2', GIT_CONFIG_KEY_0='credential.helper', GIT_CONFIG_VALUE_0='',
                          GIT_CONFIG_KEY_1='core.hooksPath', GIT_CONFIG_VALUE_1=str(hooks))
        def git(*args):
            return subprocess.check_output(['git', '--git-dir', str(destination), *args],
                                           env=verify_env, text=True, stderr=subprocess.PIPE).strip()
        if git('rev-parse', 'HEAD') != package['revision'] or git('rev-parse', 'HEAD^{tree}') != package['tree']:
            raise ValueError('Dependency Git commit/tree mismatch.')
        git('fsck', '--full', '--strict')
        if not package.get('tags'):
            raise ValueError('Authentic version tags are required.')
        for tag, oid in package['tags'].items():
            if git('rev-parse', 'refs/tags/' + tag) != oid or git('rev-parse', 'refs/tags/' + tag + '^{}') != package['revision']:
                raise ValueError('Dependency version tag differs from the reviewed snapshot.')
        original = package['sourceURL'].removesuffix('.git')
        for url in (original, original + '.git'):
            config.append(('url.' + destination.as_uri() + '.insteadOf', url))
    env['GIT_CONFIG_COUNT'] = str(len(config))
    for index, (key, value) in enumerate(config):
        env['GIT_CONFIG_KEY_' + str(index)] = key
        env['GIT_CONFIG_VALUE_' + str(index)] = value
    print(f'TTermite vendored_packages={len(packages)} archive_hash_checks=passed git_network=disabled', flush=True)
    return env


if __name__ == '__main__':
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment-file', type=Path)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    environment = configure(ROOT)
    if arguments.environment_file:
        # Only explicit, non-secret Git controls; never serialize the inherited environment.
        controls = {key: environment[key] for key in ('GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL',
                    'GIT_TERMINAL_PROMPT', 'GIT_ALLOW_PROTOCOL', 'GIT_CONFIG_COUNT')}
        for index in range(int(environment['GIT_CONFIG_COUNT'])):
            for prefix in ('GIT_CONFIG_KEY_', 'GIT_CONFIG_VALUE_'):
                controls[prefix + str(index)] = environment[prefix + str(index)]
        arguments.environment_file.write_text(json.dumps(controls, indent=2) + '\n')
    command = arguments.command[1:] if arguments.command[:1] == ['--'] else arguments.command
    if command:
        sys.exit(subprocess.run(command, env=environment, cwd=ROOT).returncode)
