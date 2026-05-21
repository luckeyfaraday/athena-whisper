from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class InjectionResult:
    inserted: bool
    backend: str
    detail: str


class TextInjector(Protocol):
    backend_name: str

    def inject(self, text: str) -> InjectionResult:
        ...


def set_clipboard_text(text: str, session_type: str | None = None) -> str:
    session = (session_type or "").lower()

    if session == "wayland" and shutil.which("wl-copy"):
        subprocess.run(["wl-copy"], input=text, text=True, check=True)
        return "wl-copy"
    if shutil.which("xclip"):
        subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, check=True)
        return "xclip"
    if shutil.which("xsel"):
        subprocess.run(["xsel", "--clipboard", "--input"], input=text, text=True, check=True)
        return "xsel"

    try:
        import pyperclip

        pyperclip.copy(text)
        return "pyperclip"
    except Exception as exc:
        raise RuntimeError(
            "No clipboard tool available. Install xclip/xsel on X11 or wl-clipboard on Wayland."
        ) from exc


@dataclass(frozen=True)
class ClipboardOnlyInjector:
    session_type: str | None = None
    backend_name: str = "clipboard-only"

    def inject(self, text: str) -> InjectionResult:
        tool = set_clipboard_text(text, self.session_type)
        return InjectionResult(
            inserted=False,
            backend=self.backend_name,
            detail=f"Copied text to clipboard with {tool}; paste manually.",
        )
