#!/usr/bin/env bash
# Every check, on this machine, before every push. There is no CI on purpose.
#   tools/test_local.sh          unit tests, stage sim, screenshots, a real window for a few seconds
#   tools/test_local.sh --quick  unit tests only
#   tools/test_local.sh --exe    ...and build the Windows exe and start it for a few seconds
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -f .venv/Scripts/python.exe ]]; then PY=.venv/Scripts/python; else PY=.venv/bin/python; fi
step() { echo; echo "==> $*"; }
fail() { echo "FAILED: $*"; exit 1; }

step "1. Unit tests (headless)"
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy "$PY" -m unittest -q 2>&1 | tail -n 3
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy "$PY" -m unittest -q >/dev/null 2>&1 || fail "unit tests"
[[ "${1:-}" == "--quick" ]] && { echo "Quick tests passed."; exit 0; }

step "2. The autopilot plays the stage (god mode must clear it)"
"$PY" tools/sim.py god | tail -n 1 | tee /dev/stderr | grep -q "cleared True" || fail "stage not cleared"

step "3. Screenshots -> shots/sheet.png"
"$PY" tools/shots.py | tail -n 1

step "4. A real window, vsync and GPU scaling, 180 frames"
IRONVOLT_FRAMES=180 "$PY" run.py >/dev/null 2>&1 || fail "real window"

if [[ "${1:-}" == "--exe" ]]; then
    step "5. Windows exe (PyInstaller, one folder)"
    "$PY" -m pip install --quiet pyinstaller==6.22.3
    "$PY" -m PyInstaller --noconfirm --clean --windowed --name Ironvolt --distpath dist --workpath build/pyi \
        run.py >/dev/null 2>&1 || fail "exe build"
    IRONVOLT_FRAMES=120 ./dist/Ironvolt/Ironvolt.exe || fail "exe run"
fi
echo; echo "All local checks passed."
