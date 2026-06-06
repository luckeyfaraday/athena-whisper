#!/usr/bin/env bash
# Build the Athena Dictate Linux app with PyInstaller.
# Run on Linux, from the project root:  bash build/build-linux.sh
# Output: dist/Athena Dictate/Athena Dictate  (+ a .desktop launcher)
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

# Emit a .desktop launcher pointing at the built binary so it can be pinned
# to the app menu / dock.
APP_DIR="$ROOT/dist/Athena Dictate"
DESKTOP="$APP_DIR/athena-dictate.desktop"
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Athena Dictate
Comment=Local speech-to-text dictation widget
Exec="$APP_DIR/Athena Dictate"
Icon=$ROOT/build/icons/athena.png
Terminal=false
Categories=Utility;AudioVideo;
EOF

echo ""
echo "Built: $APP_DIR/Athena Dictate"
echo "Launcher: $DESKTOP"
echo ""
echo "To install for your user:"
echo "  cp '$DESKTOP' ~/.local/share/applications/"
echo "Linux dictation also needs system tools (xdotool/xclip on X11) on PATH."
