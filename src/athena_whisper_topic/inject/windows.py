from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass

from .base import InjectionResult, set_clipboard_text

VK_CONTROL = 0x11
VK_V = 0x56
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("union", INPUT_UNION),
    ]


def _send_ctrl_v() -> None:
    user32 = ctypes.windll.user32
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_V, 0, 0, 0)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def _send_unicode_char(char: str) -> None:
    code = ord(char)
    inputs = (INPUT * 2)(
        INPUT(1, INPUT_UNION(ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, 0))),
        INPUT(1, INPUT_UNION(ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0))),
    )
    sent = ctypes.windll.user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
    if sent != 2:
        raise ctypes.WinError()


def _send_unicode_text(text: str, delay_seconds: float) -> None:
    for char in text:
        if ord(char) > 0xFFFF:
            encoded = char.encode("utf-16-le")
            for index in range(0, len(encoded), 2):
                _send_unicode_char(chr(int.from_bytes(encoded[index:index + 2], "little")))
        else:
            _send_unicode_char(char)
        if delay_seconds:
            time.sleep(delay_seconds)


@dataclass(frozen=True)
class WindowsClipboardPasteInjector:
    paste_delay_seconds: float = 0.08
    backend_name: str = "windows-clipboard-paste"

    def inject(self, text: str) -> InjectionResult:
        tool = set_clipboard_text(text, "windows")
        time.sleep(self.paste_delay_seconds)
        _send_ctrl_v()
        return InjectionResult(
            inserted=True,
            backend=self.backend_name,
            detail=f"Copied text to clipboard with {tool} and sent Ctrl+V.",
        )


@dataclass(frozen=True)
class WindowsKeystrokeInjector:
    char_delay_seconds: float = 0.001
    backend_name: str = "windows-keystrokes"

    def inject(self, text: str) -> InjectionResult:
        _send_unicode_text(text, self.char_delay_seconds)
        return InjectionResult(
            inserted=True,
            backend=self.backend_name,
            detail="Typed text with Windows SendInput unicode keystrokes.",
        )
