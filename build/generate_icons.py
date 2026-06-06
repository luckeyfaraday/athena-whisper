"""Rasterize the app SVG into platform icon formats.

Renders ``src/athena_whisper_topic/assets/athena-app-icon.svg`` at several sizes
using Qt's SVG renderer, then writes:

- ``build/icons/athena.ico``  (Windows, multi-resolution)
- ``build/icons/athena.icns`` (macOS, multi-resolution)
- ``build/icons/athena.png``  (Linux, 512x512)
- ``build/icons/athena-<n>.png`` per-size PNGs (used by some Linux installers)

Run with the project venv:  ``.venv/Scripts/python build/generate_icons.py``
Requires PyQt6 (with QtSvg) and Pillow, both dev/build-time only.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SVG_PATH = ROOT / "src" / "athena_whisper_topic" / "assets" / "athena-app-icon.svg"
OUT_DIR = ROOT / "build" / "icons"
SIZES = [16, 24, 32, 48, 64, 128, 256, 512, 1024]


def render_png(size: int) -> Path:
    """Render the SVG to a square PNG of the given size; return its path."""
    renderer = QSvgRenderer(str(SVG_PATH))
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    out = OUT_DIR / f"athena-{size}.png"
    image.save(str(out), "PNG")
    return out


def main() -> None:
    if not SVG_PATH.exists():
        raise SystemExit(f"SVG not found: {SVG_PATH}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # QApplication is required to initialize the Qt graphics stack.
    _app = QApplication([])

    png_paths = {size: render_png(size) for size in SIZES}
    pngs = [Image.open(p) for p in png_paths.values()]

    # Windows .ico — embed the common Windows icon sizes.
    ico_sizes = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]
    Image.open(png_paths[256]).save(OUT_DIR / "athena.ico", sizes=ico_sizes)

    # macOS .icns — Pillow picks the resolutions it needs from the source.
    Image.open(png_paths[1024]).save(OUT_DIR / "athena.icns")

    # Linux — a single 512x512 PNG is the conventional desktop icon.
    Image.open(png_paths[512]).save(OUT_DIR / "athena.png")

    for img in pngs:
        img.close()

    print(f"Wrote icons to {OUT_DIR}")
    for name in ("athena.ico", "athena.icns", "athena.png"):
        print(f"  - {name}")


if __name__ == "__main__":
    main()
