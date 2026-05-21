from athena_whisper_topic.inject.selection import InjectionEnvironment, select_injector
from athena_whisper_topic.inject.x11 import X11KeystrokeInjector


def test_selects_x11_clipboard_paste_when_xdotool_and_clipboard_available() -> None:
    env = InjectionEnvironment(
        session_type="x11",
        has_xdotool=True,
        has_wtype=False,
        has_ydotool=False,
        has_clipboard_tool=True,
    )
    assert select_injector("auto", env).backend_name == "x11-clipboard-paste"


def test_selects_x11_direct_type_when_clipboard_tool_missing() -> None:
    env = InjectionEnvironment(
        session_type="x11",
        has_xdotool=True,
        has_wtype=False,
        has_ydotool=False,
        has_clipboard_tool=False,
    )
    assert select_injector("auto", env).backend_name == "x11-direct-type"


def test_can_select_x11_terminal_paste_explicitly() -> None:
    assert select_injector("x11-terminal-paste").backend_name == "x11-terminal-paste"


def test_can_select_x11_terminal_shift_insert_paste_explicitly() -> None:
    backend = select_injector("x11-terminal-shift-insert-paste").backend_name
    assert backend == "x11-terminal-shift-insert-paste"


def test_can_select_x11_keystrokes_explicitly() -> None:
    assert select_injector("x11-keystrokes").backend_name == "x11-keystrokes"


def test_x11_keystrokes_has_modifier_release_delay() -> None:
    injector = X11KeystrokeInjector()
    assert injector.startup_delay_ms >= 100


def test_selects_wayland_clipboard_paste_when_wtype_and_clipboard_available() -> None:
    env = InjectionEnvironment(
        session_type="wayland",
        has_xdotool=False,
        has_wtype=True,
        has_ydotool=False,
        has_clipboard_tool=True,
    )
    assert select_injector("auto", env).backend_name == "wayland-clipboard-paste"


def test_falls_back_to_clipboard_only() -> None:
    env = InjectionEnvironment(
        session_type="x11",
        has_xdotool=False,
        has_wtype=False,
        has_ydotool=False,
        has_clipboard_tool=False,
    )
    assert select_injector("auto", env).backend_name == "clipboard-only"
