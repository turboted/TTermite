#!/bin/bash
set -euo pipefail
task_root="$(cd "$(dirname "$0")/.." && pwd)"
task_developer="$(xcode-select -p)"
if [[ "$task_developer" == *Xcode.app/Contents/Developer && -d "$task_developer/Platforms/MacOSX.platform" ]]; then
    unset SWIFTPM_CUSTOM_LIBS_DIR SWIFT_EXEC SWIFT_EXEC_MANIFEST
    export SDKROOT="$(xcrun --sdk macosx --show-sdk-path)"
    exec xcrun swift "$@" -Xswiftc -plugin-path -Xswiftc "$task_developer/Platforms/MacOSX.platform/Developer/usr/lib/swift/host/plugins"
fi
python3 "$task_root/scripts/prepare-toolchain.py"
export SWIFTPM_CUSTOM_LIBS_DIR="$task_root/.build/toolchain"
export SWIFT_EXEC_MANIFEST="$task_root/scripts/manifest-swiftc.sh"
export SWIFT_EXEC="$task_root/scripts/manifest-swiftc.sh"
export CLANG_MODULE_CACHE_PATH="$task_root/.build/module-cache"
export SDKROOT="${TTERMITE_SDK:-/Library/Developer/CommandLineTools/SDKs/MacOSX15.sdk}"
exec /usr/bin/swift "$@" -Xswiftc -vfsoverlay -Xswiftc "$task_root/.build/toolchain/headers.json"
