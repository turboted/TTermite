#!/bin/bash
# Build and test this exact release source. Publishing is handled by TGitSync.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 scripts/release-app.py "$@"
