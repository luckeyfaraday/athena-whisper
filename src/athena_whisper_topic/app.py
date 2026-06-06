"""GUI entry point for the packaged desktop app.

This launches the dictation widget directly with no command-line parsing, so a
double-clicked executable / .app / .desktop launcher opens straight into the
floating widget. Configuration is loaded from the usual default locations
(``./athena-dictate.toml`` or ``~/.config/athena-dictate/config.toml``) plus
``ATHENA_DICTATE_*`` environment overrides.
"""

from __future__ import annotations

import sys

from .config import DictationConfig


def _show_fatal_error(message: str) -> None:
    """Show a GUI message box on fatal startup errors.

    In a windowed (no-console) build, an uncaught exception would otherwise
    vanish silently, so surface it in a dialog when possible and fall back to
    stderr.
    """
    try:
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
        except ImportError:
            from PySide6.QtWidgets import QApplication, QMessageBox  # type: ignore

        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "Athena Dictate", message)
    except Exception:
        pass
    print(message, file=sys.stderr)


def main() -> int:
    """Load config and launch the dictation widget. Returns a process exit code."""
    try:
        cfg = DictationConfig.from_default_locations().with_env_overrides()
    except Exception as exc:  # pragma: no cover - defensive startup guard
        _show_fatal_error(f"Failed to load configuration:\n{exc}")
        return 1

    try:
        from .widget import launch_widget
    except ImportError as exc:
        _show_fatal_error(
            "The dictation widget requires PyQt6 or PySide6.\n\n"
            f"Import error: {exc}"
        )
        return 1

    launch_widget(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
