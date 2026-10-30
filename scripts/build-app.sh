#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
xcodegen generate
exec xcodebuild -project TTermite.xcodeproj -scheme TTermite -configuration Debug \
  -destination 'platform=macOS' -derivedDataPath .build/xcode \
  -clonedSourcePackagesDirPath .build/xcode-packages -jobs 4 "${@:-build}"
