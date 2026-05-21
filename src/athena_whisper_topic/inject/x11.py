from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

from .base import InjectionResult, set_clipboard_text


_MODIFIER_KEYS = [
    "Control_L",
    "Control_R",
    "Shift_L",
    "Shift_R",
    "Alt_L",
    "Alt_R",
    "Super_L",
    "Super_R",
    "Meta_L",
    "Meta_R",
]


def release_modifiers() -> None:
    subprocess.run(["xdotool", "keyup", *_MODIFIER_KEYS], check=False)


@dataclass(frozen=True)
class X11ClipboardPasteInjector:
    backend_name: str = "x11-clipboard-paste"

    def inject(self, text: str) -> InjectionResult:
        tool = set_clipboard_text(text, "x11")
        subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+v"], check=True)
        return InjectionResult(
            inserted=True,
            backend=self.backend_name,
            detail=f"Copied with {tool} and sent Ctrl+V using xdotool.",
        )


@dataclass(frozen=True)
class X11TerminalPasteInjector:
    backend_name: str = "x11-terminal-paste"

    def inject(self, text: str) -> InjectionResult:
        tool = set_clipboard_text(text, "x11")
        subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+shift+v"], check=True)
        return InjectionResult(
            inserted=True,
            backend=self.backend_name,
            detail=f"Copied with {tool} and sent Ctrl+Shift+V using xdotool.",
        )


@dataclass(frozen=True)
class X11TerminalShiftInsertPasteInjector:
    backend_name: str = "x11-terminal-shift-insert-paste"

    def inject(self, text: str) -> InjectionResult:
        tool = set_clipboard_text(text, "x11")
        subprocess.run(["xdotool", "key", "--clearmodifiers", "shift+Insert"], check=True)
        return InjectionResult(
            inserted=True,
            backend=self.backend_name,
            detail=f"Copied with {tool} and sent Shift+Insert using xdotool.",
        )


@dataclass(frozen=True)
class X11DirectTypeInjector:
    backend_name: str = "x11-direct-type"

    def inject(self, text: str) -> InjectionResult:
        subprocess.run(["xdotool", "type", "--clearmodifiers", "--delay", "0", text], check=True)
        return InjectionResult(
            inserted=True,
            backend=self.backend_name,
            detail="Typed text using xdotool.",
        )


@dataclass(frozen=True)
class X11KeystrokeInjector:
    backend_name: str = "x11-keystrokes"
    delay_ms: int = 2
    startup_delay_ms: int = 250

    def inject(self, text: str) -> InjectionResult:
        lines = text.splitlines()
        if not lines:
            return InjectionResult(
                inserted=False,
                backend=self.backend_name,
                detail="No text to type.",
            )

        release_modifiers()
        time.sleep(self.startup_delay_ms / 1000)
        release_modifiers()

        for index, line in enumerate(lines):
            if line:
                subprocess.run(
                    [
                        "xdotool",
                        "type",
                        "--clearmodifiers",
                        "--delay",
                        str(self.delay_ms),
                        line,
                    ],
                    check=True,
                )
            if index < len(lines) - 1:
                release_modifiers()
                subprocess.run(["xdotool", "key", "--clearmodifiers", "Return"], check=True)

        return InjectionResult(
            inserted=True,
            backend=self.backend_name,
            detail="Typed text as synthetic keystrokes using xdotool; clipboard was not used.",
        )
