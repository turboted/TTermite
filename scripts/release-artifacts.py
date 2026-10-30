#!/usr/bin/env python3
"""Prepare local release assets from a clean commit; never tag, push or publish."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def run(*args, cwd=None):
    return subprocess.check_output(list(args), cwd=cwd, text=True).strip()


def clean_revision(root):
    if run('git', 'rev-parse', '--show-toplevel', cwd=root) != str(root.resolve()):
        raise ValueError('Run from a complete TTermite repository, not an enclosing repository.')
    if run('git', 'rev-parse', '--is-shallow-repository', cwd=root) != 'false':
        raise ValueError('Use a full clone (git fetch --unshallow first).')
    if run('git', 'status', '--porcelain', '--untracked-files=normal', cwd=root):
        raise ValueError('Commit all intended changes before packaging a release.')
    return run('git', 'rev-parse', 'HEAD', cwd=root)


def source_bundle(root, destination):
    revision = clean_revision(root)
    refs = ['HEAD']
    branch = subprocess.run(['git', 'symbolic-ref', '--quiet', 'HEAD'], cwd=root, text=True, capture_output=True)
    if branch.returncode == 0:
        refs.append(branch.stdout.strip())
    subprocess.run(['git', 'bundle', 'create', str(destination), *refs], cwd=root, check=True)
    subprocess.run(['git', 'bundle', 'verify', str(destination)], cwd=root, check=True, stdout=subprocess.DEVNULL)
    # HEAD-only bundles also clone correctly when packaging a detached tag checkout.
    if revision not in run('git', 'bundle', 'list-heads', str(destination), cwd=root):
        raise ValueError('The source bundle does not contain the release revision.')


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def validate_history(history, revision, version, build):
    if (history.get('version') != version or history.get('build') != build
            or history.get('revision') != revision or history.get('dirty') is not False):
        raise ValueError('App version/history does not match this clean commit; rebuild first.')
    releases, commits = history['releases'], history['commits']
    ids = [c['id'] for c in commits]
    mapped = [r['commitIDs'][0] for r in releases if len(r['commitIDs']) == 1]
    if (not releases or releases[0]['version'] != version or releases[0]['commitIDs'] != [revision]
            or len(mapped) != len(releases) or len(mapped) != len(set(mapped)) or set(mapped) != set(ids)):
        raise ValueError('Each release record must correspond to exactly one actual commit.')


def prepare(root, app, output):
    root, app, output = root.resolve(), app.resolve(), output.resolve()
    revision = clean_revision(root)
    privacy_spec = importlib.util.spec_from_file_location('release_support', root / 'scripts/audit-release-support.py')
    privacy = importlib.util.module_from_spec(privacy_spec)
    privacy_spec.loader.exec_module(privacy)
    privacy.require_source_publishable(root, revision)
    checks = json.loads((root / 'build/verification/release-checks.json').read_text())
    if checks.get('revision') != revision or any(checks.get(k) != 'passed' for k in ['python', 'xctest', 'core', 'localizations']):
        raise ValueError('Run bash scripts/release.sh to test this exact commit before packaging.')
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    version, build = info['CFBundleShortVersionString'], info['CFBundleVersion']
    history_paths = list((app / 'Contents/Resources').rglob('AppHistory.json'))
    if len(history_paths) != 1:
        raise ValueError('Expected exactly one bundled AppHistory.json.')
    spec = importlib.util.spec_from_file_location('release_history', root / 'scripts/generate-app-history.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    source_version, source_build = generator.version_settings((root / 'project.yml').read_text())
    if (version, build) != (source_version, str(source_build)):
        raise ValueError('The binary version differs from committed project.yml.')
    history = json.loads(history_paths[0].read_text())
    validate_history(history, revision, version, build)
    catalog = json.loads(next((app / 'Contents/Resources').rglob('ComponentCatalog.json')).read_text())
    if catalog['version'] != version or catalog['revision'] != revision or any(i['status'] == 'review' for i in catalog['items']):
        raise ValueError('Component/license evidence needs review before release.')
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    executable = app / 'Contents/MacOS' / info['CFBundleExecutable']
    architectures = run('lipo', '-archs', str(executable)).split()
    if set(architectures) != {'arm64', 'x86_64'}:
        raise ValueError('Expected an arm64/x86_64 universal macOS app.')
    if output.exists():
        manifest = json.loads((output / 'release-manifest.json').read_text())
        if manifest['revision'] != revision or manifest['version'] != version:
            raise ValueError('Existing output belongs to another commit. Preserve it and choose a new output directory.')
        for item in manifest['assets']:
            if Path(item['name']).name != item['name'] or sha256(output / item['name']) != item['sha256']:
                raise ValueError('Existing release files differ from their manifest; review them before replacing.')
        print(f'Existing verified release assets retained: {output}')
        return manifest
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.release-', dir=output.parent) as directory:
        stage = Path(directory)
        downloads = stage / 'assets'; downloads.mkdir()
        package = stage / f'TTermite-{version}'; package.mkdir()
        subprocess.run(['ditto', str(app), str(package / 'TTermite.app')], check=True)
        for name in ['LICENSE', 'THIRD_PARTY_NOTICES.md']:
            shutil.copy2(root / name, package / name)
        (package / 'INSTALL.txt').write_text(
            'TTermite for macOS 15+\nMove TTermite.app to Applications. This is an ad-hoc signed, unnotarized build. '
            'If macOS blocks it, use Apple\'s Privacy & Security guidance or build from the matching source bundle.\n'
            '將 TTermite.app 移至「應用程式」。此版本採 ad-hoc 簽章，未公證；也可從對應來源自行建置。\n'
            '将 TTermite.app 移至“应用程序”。此版本采用 ad-hoc 签名，未公证；也可从对应源代码自行构建。\n', encoding='utf-8')
        zip_path = downloads / f'TTermite-{version}-macOS-universal.zip'
        subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(package), str(zip_path)], check=True)
        source_bundle(root, downloads / f'TTermite-{version}-source.bundle')
        release = history['releases'][0]
        notes = [f'# TTermite {version}', '', f'Commit: `{revision}` · Build: {build}', '']
        for language, title in [('en', 'English'), ('zh-Hans', '简体中文'), ('zh-Hant', '繁體中文')]:
            notes += [f'## {title}', '', release['titles'][language], ''] + ['- ' + n for n in release['notes'][language]] + ['']
        notes += ['## Adopted sources / 採用來源 / 采用来源', '', '| Project | Version | Commit |', '| --- | --- | --- |']
        for source in history['sources']:
            repository, sha = source['repository'], source['revision']
            notes.append(f'| [{repository}](https://github.com/{repository}) | {source["version"]} | [`{sha[:12]}`](https://github.com/{repository}/commit/{sha}) |')
        notes.append('')
        notes += ['## Downloads / 下載 / 下载', '',
                  '- `macOS-universal.zip`: macOS 15+, Apple Silicon and Intel; ad-hoc signed, not notarized.',
                  '- `source.bundle`: complete source Git history. Clone with `git clone FILE.bundle TTermite`, then follow README.',
                  '- `SHA256SUMS.txt`: verify downloaded files with `shasum -a 256 -c SHA256SUMS.txt`.', '',
                  'The source bundle includes project sources, licenses, notices and pinned package references. '
                  'First-time dependency resolution still requires network access.', '']
        (downloads / 'RELEASE_NOTES.md').write_text('\n'.join(notes), encoding='utf-8')
        assets = [dict(name=p.name, sha256=sha256(p), bytes=p.stat().st_size) for p in sorted(downloads.iterdir())]
        sums = ''.join(f'{item["sha256"]}  {item["name"]}\n' for item in assets)
        (downloads / 'SHA256SUMS.txt').write_text(sums)
        assets.append(dict(name='SHA256SUMS.txt', sha256=sha256(downloads / 'SHA256SUMS.txt'), bytes=(downloads / 'SHA256SUMS.txt').stat().st_size))
        manifest = dict(schemaVersion=1, version=version, build=build, tag='v' + version, revision=revision,
                        architectures=architectures, signing='ad-hoc', notarized=False, tests=checks,
                        assets=assets, sources=history['sources'])
        (downloads / 'release-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        clean_revision(root) # Reject source changes that occurred while packaging.
        if run('git', 'rev-parse', 'HEAD', cwd=root) != revision:
            raise ValueError('HEAD changed while packaging; discard this candidate and retry.')
        downloads.rename(output)
    print(f'Prepared local assets: {output}')
    print(f'GitHub Release tag: v{version}; target commit: {revision}')
    print('No tag, Git push or GitHub publication was performed.')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, default=ROOT / 'build/TTermite.app')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        info = plistlib.loads((args.app / 'Contents/Info.plist').read_bytes())
        prepare(ROOT, args.app, args.output or ROOT / 'build/releases' / ('v' + info['CFBundleShortVersionString']))
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
