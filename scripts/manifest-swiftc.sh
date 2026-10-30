#!/bin/bash
set -euo pipefail
task_root="$(cd "$(dirname "$0")/.." && pwd)"
exec /Library/Developer/CommandLineTools/usr/bin/swiftc -vfsoverlay "$task_root/.build/toolchain/headers.json" "$@"
