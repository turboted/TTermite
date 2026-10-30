# Exact-version App release sources

These sources reconstruct each original development stage as a new, current-date source commit. `source-rebuild-map.json` records original source identity. Original development commits and remote tags remain unchanged. A reconstructed source is not the original historical SHA repaired in place. Existing tags targeting another SHA require a separate publication decision; these scripts never publish, move tags or force-push.

## Environment and recipe

macOS 15+, full Xcode 26.3 with macOS SDK 26.2, Swift 6.2.4, installed Metal Toolchain 17C7003j, XcodeGen 2.46, Python 3, Git, and network access to the public dependencies pinned in Package.resolved. Install the Metal component with `xcodebuild -downloadComponent MetalToolchain` before building. The recipe reads Xcode component metadata and explicitly registers the installed toolchain search directory for the build; no personal HOME, credentials, compiler cache or hard-coded machine paths are needed.

TGitSync settings, from an independent full clone checked out at the exact selected source SHA:

```text
Test command: (empty)
Build command: bash scripts/release.sh
App path: build/TTermite.app
Build command includes all tests: enabled
```

`python3 scripts/release-app.py` is the equivalent entry. Each SHA contains both entries and the tests and helper scripts it uses. Tests run in Debug and the App builds in Release; core and Python tests run when present at this source stage. Native tests explicitly verify their isolated Foundation home. Build output is limited to ignored folders. The build checks unchanged HEAD/tracked sources, exact App/catalog version, arm64 and x86_64, and ad-hoc signature. Apps are not notarized.

## Verification and delivery

Each final source must be tested in a new detached clone with initially empty HOME and disabled personal Git configuration, hooks and credentials. A build result is distinct from complete privacy review, isolated product acceptance and GitHub publication. Local logs, screenshots and runtime evidence belong only in ignored build/verification folders. TGitSync produces the App ZIP, build-provenance.json and SHA256SUMS.txt from each exact source; all GitHub asset receipts must match before publication is reported complete. No latest App substitution or source-only fallback qualifies as App delivery.
