#!/usr/bin/env python3
"""Verify this commit's app; this does not certify source history or GitHub publication."""
import json
import os
from pathlib import Path
import plistlib
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def verify(root, app, require_history=True, expected_version=None):
    def run(*args):
        return subprocess.check_output(args, cwd=root, text=True).strip()
    revision = run('git', 'rev-parse', 'HEAD')
    if run('git', 'status', '--porcelain', '--untracked-files=normal'):
        raise ValueError('Source must remain clean after building.')
    if app.is_symlink() or not app.is_dir():
        raise ValueError('Expected a real .app directory.')
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    import re
    project = (root / 'project.yml').read_text()
    version = re.search(r'MARKETING_VERSION:\s*"([^"]+)"', project)[1]
    if expected_version is not None and version != expected_version:
        raise ValueError('Source App version differs from the release version; rebuild the source with its own version, not a renamed binary.')
    build = re.search(r'CURRENT_PROJECT_VERSION:\s*"([^"]+)"', project)[1]
    if (info.get('CFBundleShortVersionString'), info.get('CFBundleVersion'), info.get('CFBundleIdentifier')) != (version, build, 'app.ttermite.app'):
        raise ValueError('App identity/version/build differs from committed source.')
    name = info['CFBundleExecutable']
    if not name or Path(name).name != name or name in ('.', '..'):
        raise ValueError('Invalid executable name.')
    import importlib.util
    policy_spec = importlib.util.spec_from_file_location('source_policy', Path(__file__).with_name('audit-release-support.py'))
    policy = importlib.util.module_from_spec(policy_spec); policy_spec.loader.exec_module(policy)
    for member in app.rglob('*'):
        if member.is_symlink() and not member.resolve().is_relative_to(app.resolve()):
            raise ValueError('External app symlink.')
        if policy.privacy_path(member.relative_to(app).as_posix()):
            raise ValueError('App contains local-state or credential paths.')
    histories = list((app / 'Contents/Resources').rglob('AppHistory.json'))
    if len(histories) > 1 or (require_history and not histories):
        raise ValueError('Expected one history resource for this version.')
    if histories:
        if histories[0].stat().st_size > 8 * 1024 * 1024: raise ValueError('History exceeds 8 MiB.')
        history = json.loads(histories[0].read_text())
        if any(history.get(k) != v for k, v in dict(version=version, build=build, revision=revision, dirty=False).items()):
            raise ValueError('Bundled history differs from the selected commit.')
    executable = app / 'Contents/MacOS' / name
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError('Expected an executable Mach-O.')
    if info.get('LSMinimumSystemVersion') != '15.0':
        raise ValueError('Unexpected minimum macOS version.')
    architectures = run('lipo', '-archs', str(executable)).split()
    if set(architectures) != {'arm64', 'x86_64'}:
        raise ValueError('Expected a universal app.')
    run('codesign', '--verify', '--deep', '--strict', str(app))
    return dict(version=version, build=build, revision=revision, architectures=architectures,
                signature='codesign verified', notarized=False, githubPublished=False,
                appPathPrivacy='known-path checks passed; not exhaustive clearance')


if __name__ == '__main__':
    result = verify(ROOT, ROOT / 'build/TTermite.app')
    output = ROOT / 'build/verification/app-validation.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
