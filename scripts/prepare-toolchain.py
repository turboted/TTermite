"""Work around obsolete CLT private interfaces without modifying system files."""
from pathlib import Path
import json
import shutil

root=Path(__file__).resolve().parents[1]
cache=root/'.build/toolchain'
cache.mkdir(parents=True,exist_ok=True)
system=Path('/Library/Developer/CommandLineTools/usr/lib/swift/pm')
for name in ['ManifestAPI','PluginAPI']:
    dest=cache/name
    if not dest.exists():shutil.copytree(system/name,dest)
    for private in dest.rglob('*.private.swiftinterface'):
        public=private.with_name(private.name.replace('.private.swiftinterface','.swiftinterface'))
        if public.exists():shutil.copy2(public,private)

empty=cache/'empty.modulemap'
empty.write_text('// Obsolete SwiftBridging map hidden for this build only.\n')
old=Path('/Library/Developer/CommandLineTools/usr/include/swift/module.modulemap')
roots=[]
if old.exists() and (old.parent/'bridging.modulemap').exists():
    roots.append({'type':'file','name':str(old),'external-contents':str(empty)})
(cache/'headers.json').write_text(json.dumps({'version':0,'use-external-names':False,'roots':roots}))
