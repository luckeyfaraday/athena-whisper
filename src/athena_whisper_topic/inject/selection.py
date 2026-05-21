from __future__ import annotations

import os
import platform
import shutil
from dataclasses import dataclass

from .base import ClipboardOnlyInjector, TextInjector
from .uinput import YdotoolTypeInjector
from .wayland import WaylandClipboardPasteInjector
from .windows import WindowsClipboardPasteInjector, WindowsKeystrokeInjector
from .x11 import (
    X11ClipboardPasteInjector,
    X11DirectTypeInjector,
    X11KeystrokeInjector,
    X11TerminalPasteInjector,
    X11TerminalShiftInsertPasteInjector,
)


@dataclass(frozen=True)
class InjectionEnvironment:
    session_type: str | None
    has_xdotool: bool
    has_wtype: bool
    has_ydotool: bool
    has_clipboard_tool: bool
    is_windows: bool = False

    @classmethod
    def detect(cls) -> "InjectionEnvironment":
        session_type = os.getenv("XDG_SESSION_TYPE")
        clipboard_tools = ("wl-copy", "xclip", "xsel")
        return cls(
            session_type=session_type,
            has_xdotool=shutil.which("xdotool") is not None,
            has_wtype=shutil.which("wtype") is not None,
            has_ydotool=shutil.which("ydotool") is not None,
            has_clipboard_tool=any(shutil.which(tool) is not None for tool in clipboard_tools),
            is_windows=platform.system().lower() == "windows",
        )


def select_injector(
    backend: str = "auto",
    env: InjectionEnvironment | None = None,
) -> TextInjector:
    environment = env or InjectionEnvironment.detect()
    session = (environment.session_type or "").lower()

    if backend == "clipboard-only":
        return ClipboardOnlyInjector(environment.session_type)
    if backend == "x11-clipboard-paste":
        return X11ClipboardPasteInjector()
    if backend == "x11-terminal-paste":
        return X11TerminalPasteInjector()
    if backend == "x11-terminal-shift-insert-paste":
        return X11TerminalShiftInsertPasteInjector()
    if backend == "x11-direct-type":
        return X11DirectTypeInjector()
    if backend == "x11-keystrokes":
        return X11KeystrokeInjector()
    if backend == "wayland-clipboard-paste":
        return WaylandClipboardPasteInjector()
    if backend == "windows-clipboard-paste":
        return WindowsClipboardPasteInjector()
    if backend == "windows-keystrokes":
        return WindowsKeystrokeInjector()
    if backend == "ydotool-type":
        return YdotoolTypeInjector()
    if backend != "auto":
        raise ValueError(f"Unknown insertion backend: {backend}")

    if session == "x11" and environment.has_xdotool and environment.has_clipboard_tool:
        return X11ClipboardPasteInjector()
    if session == "x11" and environment.has_xdotool:
        return X11DirectTypeInjector()
    if session == "wayland" and environment.has_wtype and environment.has_clipboard_tool:
        return WaylandClipboardPasteInjector()
    if environment.is_windows:
        return WindowsKeystrokeInjector()
    if environment.has_ydotool:
        return YdotoolTypeInjector()
    return ClipboardOnlyInjector(environment.session_type)
