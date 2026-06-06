#!/usr/bin/env bash
# Build the Athena Dictate macOS app and package it as a .dmg.
# Run on a Mac, from the project root:  bash build/build-macos.sh
# Output: dist/Athena Dictate.dmg  (and dist/Athena Dictate.app)
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

# Package the .app into a compressed .dmg with an Applications drag-target.
APP="$ROOT/dist/Athena Dictate.app"
DMG="$ROOT/dist/Athena Dictate.dmg"
STAGING="$(mktemp -d)"
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"
rm -f "$DMG"
hdiutil create -volname "Athena Dictate" -srcfolder "$STAGING" -ov -format UDZO "$DMG"
rm -rf "$STAGING"

echo ""
echo "Built: $DMG"
echo ""
echo "Note: the app is unsigned. On first launch, right-click the .app and"
echo "choose Open, or run: xattr -dr com.apple.quarantine '/Applications/Athena Dictate.app'"
