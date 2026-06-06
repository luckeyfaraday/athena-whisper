#!/usr/bin/env bash
# Build the Athena Dictate macOS app (.app) with PyInstaller.
# Run on a Mac, from the project root:  bash build/build-macos.sh
# Output: dist/Athena Dictate.app
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
PY="$ROOT/.venv/bin/python"

"$PY" -m pip install --upgrade pip
"$PY" -m pip install -e ".[gui]"
"$PY" -m pip install pyinstaller pillow

"$PY" build/generate_icons.py
"$PY" -m PyInstaller build/athena-dictate.spec --noconfirm --clean --distpath dist --workpath build/work

echo ""
echo "Built: dist/Athena Dictate.app"
echo "To run: open 'dist/Athena Dictate.app'"
echo ""
echo "Note: the app is unsigned. On first launch, right-click the .app and"
echo "choose Open, or run: xattr -dr com.apple.quarantine 'dist/Athena Dictate.app'"
