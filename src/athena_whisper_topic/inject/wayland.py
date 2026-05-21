from __future__ import annotations

import subprocess
from dataclasses import dataclass

from .base import InjectionResult, set_clipboard_text


@dataclass(frozen=True)
class WaylandClipboardPasteInjector:
    backend_name: str = "wayland-clipboard-paste"

    def inject(self, text: str) -> InjectionResult:
        tool = set_clipboard_text(text, "wayland")
        subprocess.run(["wtype", "-M", "ctrl", "-k", "v", "-m", "ctrl"], check=True)
        return InjectionResult(
            inserted=True,
            backend=self.backend_name,
            detail=f"Copied with {tool} and sent Ctrl+V using wtype.",
        )
