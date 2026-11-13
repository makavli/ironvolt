#!/usr/bin/env bash
# CI only: publish the current version as a GitHub release with the builds in out/ (once per version).
set -euo pipefail
v=$(python3 -c "import ironvolt; print(ironvolt.__version__)")
tag="v$v"
if gh release view "$tag" > /dev/null 2>&1; then
    echo "::notice::$tag is already released"
    exit 0
fi
gh release create "$tag" out/* --target "$GITHUB_SHA" --title "IRONVOLT $v" --notes-file notes.md
