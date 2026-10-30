#!/usr/bin/env python3
"""Test and build this exact version; no upload, tag, source or version changes."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import tempfile
import sys
ROOT=Path(__file__).resolve().parent.parent

def run(*args, env=None, stage=None):
    command = list(args)
    kit = os.environ.get('TGITSYNC_RELEASE_KIT')
    if stage:
        print(f'TTermite stage={stage}', flush=True)
        if kit:
            command = [sys.executable, str(Path(kit) / 'bin/timing.py'), '--stage', stage, '--', *command]
    subprocess.run(command, cwd=ROOT, check=True, env=env)

def prepare_dependencies():
    output = ROOT / '.build/dependency-environment.json'
    run('python3', 'scripts/release_dependencies.py', '--environment-file', str(output), stage='dependencies')
    os.environ.update(json.loads(output.read_text()))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--tests-only',action='store_true');parser.add_argument('--build-only',action='store_true');a=parser.parse_args()
    if a.tests_only and a.build_only:raise ValueError('Choose one stage.')
    os.environ['CFFIXED_USER_HOME']=os.environ['HOME']
    test_parent=ROOT/'build/verification';test_parent.mkdir(parents=True,exist_ok=True)
    test_home=Path(tempfile.mkdtemp(prefix='unit-home-',dir=test_parent));(test_home/'tmp').mkdir()
    for name,value in {'HOME':str(test_home),'CFFIXED_USER_HOME':str(test_home),'TTERMITE_TEST_HOME':str(test_home),'TMPDIR':str(test_home/'tmp')+'/', 'BERTH_TRANSIENT_STORE':'1','TTERMITE_HISTORY_PATH':str(test_home/'history.sqlite')}.items():
        os.environ['TEST_RUNNER_'+name]=value
    os.environ['TEST_RUNNER_TTERMITE_PROFILE_PREFERENCES']='1'
    os.environ['USER']=subprocess.check_output(['id','-un'],text=True).strip()
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT):raise ValueError('Use a clean committed source.')
    modules=Path(os.environ.get('CLANG_MODULE_CACHE_PATH') or ROOT/'.build/module-cache').resolve()
    modules.mkdir(parents=True,exist_ok=True)
    os.environ['CLANG_MODULE_CACHE_PATH']=str(modules)
    os.environ['SWIFTPM_MODULECACHE_OVERRIDE']=str(modules)
    prepare_dependencies()
    component=json.loads(subprocess.check_output(['xcodebuild','-showComponent','MetalToolchain','-json'],text=True))
    if component.get('status')!='installed':raise ValueError('Install the declared Metal Toolchain with xcodebuild -downloadComponent MetalToolchain before building.')
    toolchain=Path(component['toolchainSearchPath'])/'Metal.xctoolchain'
    metadata=plistlib.loads((toolchain/'ToolchainInfo.plist').read_bytes())
    if metadata['Identifier']!=component['toolchainIdentifier']:raise ValueError('Metal toolchain identity differs from Xcode component metadata.')
    run(str(toolchain/'usr/bin/metal'),'--version')
    os.environ['EXTERNAL_TOOLCHAINS_DIR']=component['toolchainSearchPath']
    run('python3','scripts/generate-app-history.py');run('xcodegen','generate')
    lock=ROOT/'TTermite.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved';lock.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'Package.resolved',lock)
    base=['xcodebuild','-project','TTermite.xcodeproj','-scheme','TTermite','-destination','platform=macOS','-clonedSourcePackagesDirPath','.build/xcode-packages','-onlyUsePackageVersionsFromResolvedFile','-toolchain',component['toolchainIdentifier'],f'MODULE_CACHE_DIR={modules}',f'CLANG_MODULE_CACHE_PATH={modules}']
    run(*base,'-derivedDataPath','.build/xcode','-jobs','4','-resolvePackageDependencies',stage='dependencies')
    if (ROOT/'scripts/generate-component-catalog.py').is_file():run('python3','scripts/generate-component-catalog.py');run('xcodegen','generate')
    jobs='4'
    release_data='.build/xcode-release'
    helper=ROOT/'.build/test-profile/PreferencesProfile.dylib'
    helper.parent.mkdir(parents=True,exist_ok=True)
    def tests():
        run('xcrun','clang','-dynamiclib','-fobjc-arc','-framework','Foundation','-mmacosx-version-min=15.0','scripts/support/PreferencesProfile.m',f'-fmodules-cache-path={modules}','-o',str(helper),stage='test-compile')
        run('codesign','--force','--sign','-',str(helper),stage='test-compile')
        if list((ROOT/'Tests').glob('test_*.py')):run('python3','-m','unittest','discover','-s','Tests','-p','test_*.py',stage='test-execute')
        run(*base,'-derivedDataPath','.build/xcode','-jobs',jobs,'-configuration','Debug','build-for-testing',stage='test-compile')
        plans=list((ROOT/'.build/xcode/Build/Products').glob('*.xctestrun'))
        if len(plans)!=1:raise ValueError('Expected exactly one complete generated XCTest plan.')
        plan=plans[0];data=plistlib.loads(plan.read_bytes());count=0
        def inject(node):
            nonlocal count
            if isinstance(node,dict):
                if 'TestBundlePath' in node:
                    count+=1
                    values=node.setdefault('EnvironmentVariables',{})
                    existing=values.get('DYLD_INSERT_LIBRARIES','')
                    testing=node.get('TestingEnvironmentVariables',{})
                    injected=testing.get('DYLD_INSERT_LIBRARIES','')
                    libraries=[x for x in (existing+':'+injected).split(':') if x]
                    libraries.append(str(helper))
                    combined=':'.join(dict.fromkeys(libraries))
                    values['DYLD_INSERT_LIBRARIES']=combined
                    values.update(HOME=str(test_home),CFFIXED_USER_HOME=str(test_home),TTERMITE_TEST_HOME=str(test_home),TTERMITE_PROFILE_PREFERENCES='1')
                    # Preserve XCTest's own injection entries in either environment dictionary.
                    if 'DYLD_INSERT_LIBRARIES' in testing:testing['DYLD_INSERT_LIBRARIES']=combined
                for value in node.values():inject(value)
            elif isinstance(node,list):
                for value in node:inject(value)
        inject(data)
        if count<1:raise ValueError('No test targets in generated XCTest plan.')
        plan.write_bytes(plistlib.dumps(data))
        run('xcodebuild','-xctestrun',str(plan),'-destination','platform=macOS','-derivedDataPath','.build/xcode','test-without-building',f'MODULE_CACHE_DIR={modules}',f'CLANG_MODULE_CACHE_PATH={modules}',stage='test-execute')
        if not (test_home/'PreferencesProfile.ready').is_file():raise ValueError('Native test preferences profile was not installed.')
        if (ROOT/'Tests/CoreIntegrationTests.swift').is_file():
            script=(ROOT/'scripts/test-core.sh').read_text();inputs=re.findall(r'(?:Berth|Tests)/[^\s\\]+\.swift',script)
            if 'Tests/CoreIntegrationTests.swift' not in inputs:raise ValueError('Missing exact core compiler inputs.')
            files=[]
            for pattern in inputs:files.extend(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern))
            (ROOT/'.build/core-tests').mkdir(parents=True,exist_ok=True)
            sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
            run('xcrun','--sdk','macosx','swiftc','-sdk',sdk,'-module-cache-path',str(modules),'-parse-as-library','-o','.build/core-tests/run',*files,'-lsqlite3',stage='test-compile');run('.build/core-tests/run',env=dict(os.environ,DYLD_INSERT_LIBRARIES=str(helper),TTERMITE_PROFILE_PREFERENCES='1',TTERMITE_TEST_HOME=os.environ['HOME']),stage='test-execute')
        if (ROOT/'scripts/check-localizations.py').is_file():run('python3','scripts/check-localizations.py','--strings-data-directory','.build/xcode/Build/Intermediates.noindex/TTermite.build/Debug/TTermite.build/Objects-normal/arm64',stage='test-execute')
    # A failed full test stage must prevent any formal Release compilation.
    if not a.build_only:
        tests()
    if not a.tests_only:
        run(*base,'-derivedDataPath',release_data,'-jobs',jobs,'-configuration','Release','build',stage='compile')
    if not a.tests_only:
        app=ROOT/'build/TTermite.app';app.parent.mkdir(exist_ok=True)
        if app.exists():shutil.rmtree(app)
        run('ditto',release_data+'/Build/Products/Release/TTermite.app',str(app));run('codesign','--verify','--deep','--strict',str(app))
        info=plistlib.loads((app/'Contents/Info.plist').read_bytes());version=json.loads((ROOT/'release-history.json').read_text())['releases'][0]['version']
        if info['CFBundleShortVersionString']!=version:raise ValueError('App version must exactly equal release version.')
        archs=subprocess.check_output(['lipo','-archs',str(app/'Contents/MacOS'/info['CFBundleExecutable'])],text=True).split()
        if set(archs)!={'arm64','x86_64'}:raise ValueError('Expected a universal app.')
        run('python3','scripts/check-release-app.py')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()!=head or subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT):raise ValueError('Build changed tracked source or HEAD.')
if __name__=='__main__':main()
