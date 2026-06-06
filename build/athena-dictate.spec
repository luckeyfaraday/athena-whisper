# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Athena Dictate.

Builds a windowed (no console) desktop app that launches the dictation widget.
Cross-platform: run on the OS you want to target (PyInstaller does not
cross-compile). The build scripts in this folder invoke it as:

    pyinstaller build/athena-dictate.spec --noconfirm --clean

Output lands in dist/:
  - Windows: dist/Athena Dictate/Athena Dictate.exe  (one-folder)
  - Linux:   dist/Athena Dictate/Athena Dictate       (one-folder binary)
  - macOS:   dist/Athena Dictate.app                   (app bundle)
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

# The spec file is run from the project root, so paths are relative to cwd.
ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / "src"
ASSETS = SRC / "athena_whisper_topic" / "assets"
ICON_DIR = ROOT / "build" / "icons"

APP_NAME = "Athena Dictate"

# A tiny launcher avoids depending on console_scripts wrappers inside the bundle.
ENTRY = ROOT / "build" / "_entry.py"
ENTRY.write_text(
    "from athena_whisper_topic.app import main\n"
    "import sys\n"
    "sys.exit(main())\n",
    encoding="utf-8",
)

datas = [(str(ASSETS), "athena_whisper_topic/assets")]
binaries = []
hiddenimports = [
    "PyQt6.QtSvg",
    "athena_whisper_topic.widget",
    "athena_whisper_topic.inject.windows",
    "athena_whisper_topic.inject.x11",
    "athena_whisper_topic.inject.wayland",
    "athena_whisper_topic.inject.uinput",
    "athena_whisper_topic.inject.selection",
]

# Native deps that ship binaries and/or data files PyInstaller can miss.
for pkg in ("faster_whisper", "ctranslate2", "sounddevice", "soundfile", "av", "onnxruntime", "tokenizers"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# Per-platform icon.
if sys.platform == "win32":
    icon = str(ICON_DIR / "athena.ico")
elif sys.platform == "darwin":
    icon = str(ICON_DIR / "athena.icns")
else:
    icon = str(ICON_DIR / "athena.png")

block_cipher = None

a = Analysis(
    [str(ENTRY)],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PySide6"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=icon,
        bundle_identifier="ai.athena.dictate",
        info_plist={
            "NSMicrophoneUsageDescription": "Athena Dictate records the microphone to transcribe your speech locally.",
            "NSHighResolutionCapable": True,
            "LSUIElement": False,
        },
    )
