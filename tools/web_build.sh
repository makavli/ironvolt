#!/usr/bin/env bash
# Builds the browser version with pygbag into out/Ironvolt-web.zip (index.html at its root, as itch.io wants).
#   bash tools/web_build.sh           build only
#   bash tools/web_build.sh --serve   build, then serve it on http://localhost:8000 to play locally
set -euo pipefail
cd "$(dirname "$0")/.."
PY=python; [ -x .venv/Scripts/python ] && PY="$PWD/.venv/Scripts/python"; [ -x .venv/bin/python ] && PY="$PWD/.venv/bin/python"
src=build/web-src
rm -rf "$src" && mkdir -p "$src" out
cp web/main.py "$src/"
cp -r ironvolt "$src/"
find "$src" -name __pycache__ -prune -exec rm -rf {} +
"$PY" -m pygbag --build --ume_block 0 --title IRONVOLT --app_name ironvolt "$src"
(cd "$src/build/web" && rm -f ../../../../out/Ironvolt-web.zip && "$PY" -c "
import sys, zipfile, os
with zipfile.ZipFile(sys.argv[1], 'w', zipfile.ZIP_DEFLATED) as z:
    for n in sorted(os.listdir('.')):
        z.write(n)
" ../../../../out/Ironvolt-web.zip)
ls -la "$src/build/web" out/Ironvolt-web.zip
if [ "${1:-}" = "--serve" ]; then
    echo "Open http://localhost:8000 (Ctrl+C stops)"
    "$PY" -m http.server 8000 -d "$src/build/web"
fi
