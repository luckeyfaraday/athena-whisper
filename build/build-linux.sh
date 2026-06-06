#!/usr/bin/env bash
# Build the Athena Dictate Linux app and package it as an .AppImage.
# Run on Linux, from the project root:  bash build/build-linux.sh
# Output: dist/Athena Dictate.AppImage  (and dist/Athena Dictate/ folder app)
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

# Assemble an AppDir and package it as a portable .AppImage.
APP_DIR="$ROOT/dist/Athena Dictate"
APPDIR="$ROOT/dist/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR"
cp -R "$APP_DIR/." "$APPDIR/"

# AppRun launches the PyInstaller binary from inside the mounted AppImage.
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/Athena Dictate" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# Top-level icon + desktop entry (required by appimagetool; Icon has no extension).
cp "$ROOT/build/icons/athena.png" "$APPDIR/athena.png"
cat > "$APPDIR/athena-dictate.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Athena Dictate
Comment=Local speech-to-text dictation widget
Exec=AppRun
Icon=athena
Terminal=false
Categories=Utility;AudioVideo;
EOF

# Fetch appimagetool once (cached in dist/). --appimage-extract-and-run avoids
# needing FUSE on the build machine / CI runner.
TOOL="$ROOT/dist/appimagetool-x86_64.AppImage"
if [ ! -x "$TOOL" ]; then
    curl -fsSL -o "$TOOL" \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$TOOL"
fi

rm -f "$ROOT/dist/Athena Dictate.AppImage"
ARCH=x86_64 "$TOOL" --appimage-extract-and-run "$APPDIR" "$ROOT/dist/Athena Dictate.AppImage"

echo ""
echo "Built: $ROOT/dist/Athena Dictate.AppImage"
echo "Run it with:  chmod +x 'Athena Dictate.AppImage' && ./'Athena Dictate.AppImage'"
echo "Linux dictation also needs system tools (xdotool/xclip on X11) on PATH."
