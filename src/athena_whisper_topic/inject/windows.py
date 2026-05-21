from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from dataclasses import dataclass

from .base import InjectionResult, set_clipboard_text


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_CONTROL = 0x11
VK_RETURN = 0x0D
VK_V = 0x56


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]


def _ensure_windows() -> None:
    if sys.platform != "win32":
        raise RuntimeError("Windows injection backends can only run on Windows.")


def _keyboard_input(
    vk: int = 0,
    scan: int = 0,
    flags: int = 0,
) -> INPUT:
    return INPUT(
        type=INPUT_KEYBOARD,
        union=INPUT_UNION(
            ki=KEYBDINPUT(
                wVk=vk,
                wScan=scan,
                dwFlags=flags,
                time=0,
                dwExtraInfo=None,
            )
        ),
    )


def _send_inputs(inputs: list[INPUT]) -> None:
    _ensure_windows()
    array_type = INPUT * len(inputs)
    sent = ctypes.windll.user32.SendInput(len(inputs), array_type(*inputs), ctypes.sizeof(INPUT))
    if sent != len(inputs):
        raise ctypes.WinError()


def _send_key(vk: int) -> None:
    _send_inputs([
        _keyboard_input(vk=vk),
        _keyboard_input(vk=vk, flags=KEYEVENTF_KEYUP),
    ])


def _send_unicode_char(char: str) -> None:
    codepoint = ord(char)
    if codepoint > 0xFFFF:
        # Send UTF-16 surrogate pairs for non-BMP characters.
        encoded = char.encode("utf-16-le")
        units = [int.from_bytes(encoded[index:index + 2], "little") for index in range(0, len(encoded), 2)]
    else:
        units = [codepoint]

    events: list[INPUT] = []
    for unit in units:
        events.append(_keyboard_input(scan=unit, flags=KEYEVENTF_UNICODE))
        events.append(_keyboard_input(scan=unit, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP))
    _send_inputs(events)


@dataclass(frozen=True)
class WindowsSendInputInjector:
    backend_name: str = "windows-sendinput"
    delay_ms: int = 1

    def inject(self, text: str) -> InjectionResult:
        _ensure_windows()
        for char in text:
            if char == "\n":
                _send_key(VK_RETURN)
            else:
                _send_unicode_char(char)
            if self.delay_ms:
                time.sleep(self.delay_ms / 1000)
        return InjectionResult(
            inserted=bool(text),
            backend=self.backend_name,
            detail="Typed text using Win32 SendInput Unicode keyboard events.",
        )


@dataclass(frozen=True)
class WindowsClipboardPasteInjector:
    backend_name: str = "windows-clipboard-paste"

    def inject(self, text: str) -> InjectionResult:
        _ensure_windows()
        tool = set_clipboard_text(text, "windows")
        _send_inputs([
            _keyboard_input(vk=VK_CONTROL),
            _keyboard_input(vk=VK_V),
            _keyboard_input(vk=VK_V, flags=KEYEVENTF_KEYUP),
            _keyboard_input(vk=VK_CONTROL, flags=KEYEVENTF_KEYUP),
        ])
        return InjectionResult(
            inserted=True,
            backend=self.backend_name,
            detail=f"Copied with {tool} and sent Ctrl+V using Win32 SendInput.",
        )
