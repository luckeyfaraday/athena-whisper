from __future__ import annotations

import sys
import tempfile
import threading
from enum import Enum, auto
from pathlib import Path

from .config import DictationConfig

try:
    from PyQt6.QtCore import QEvent, QPoint, QTimer, Qt, QThread, pyqtSignal as Signal
    from PyQt6.QtGui import QColor, QCursor, QPainter
    from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
except ImportError:
    try:
        from PySide6.QtCore import QEvent, QPoint, QTimer, Qt, QThread, Signal
        from PySide6.QtGui import QColor, QCursor, QPainter
        from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
    except ImportError:
        raise ImportError(
            "The widget UI requires PyQt6 or PySide6.\n"
            "Install with:  pip install 'athena-whisper-topic[gui]'"
        )


_TERMINAL_WM_CLASSES = frozenset({
    "xterm", "urxvt", "rxvt", "gnome-terminal", "gnome-terminal-server",
    "konsole", "alacritty", "kitty", "tilix", "xfce4-terminal", "terminator",
    "st", "lxterminal", "terminology", "hyper", "wezterm", "qterminal",
    "sakura", "eterm", "aterm",
})


def _capture_target() -> tuple[str | None, str | None]:
    """Return (focus_window, active_window).

    focus_window (getwindowfocus) is the X window that actually receives key
    events — for gnome-terminal this is the VTE child, not the top-level shell.
    active_window (getactivewindow) is the top-level WM window, used only for
    WM_CLASS detection.
    """
    import shutil
    import subprocess
    if not shutil.which("xdotool"):
        return None, None
    try:
        focus = subprocess.run(["xdotool", "getwindowfocus"], capture_output=True, text=True)
        active = subprocess.run(["xdotool", "getactivewindow"], capture_output=True, text=True)
        return focus.stdout.strip() or None, active.stdout.strip() or None
    except Exception:
        return None, None


def _is_terminal(window_id: str) -> bool:
    import shutil
    import subprocess
    if not (window_id and shutil.which("xdotool")):
        return False
    try:
        r = subprocess.run(
            ["xdotool", "getwindowclassname", window_id],
            capture_output=True, text=True,
        )
        name = r.stdout.strip().lower()
        return name in _TERMINAL_WM_CLASSES or "term" in name
    except Exception:
        return False


def _x11_paste(text: str, focus_window: str | None, class_window: str | None) -> bool:
    """Inject text into the target X window. Returns True on success.

    For terminals: xdotool type (keystroke-by-keystroke, no clipboard needed).
    For everything else: clipboard + xdotool key ctrl+v to the specific window.
    """
    import shutil
    import subprocess
    if not shutil.which("xdotool"):
        return False
    try:
        if _is_terminal(class_window or ""):
            from .inject.x11 import X11KeystrokeInjector
            X11KeystrokeInjector().inject(text)
        elif focus_window:
            from .inject.base import set_clipboard_text
            set_clipboard_text(text, "x11")
            subprocess.run(
                ["xdotool", "key", "--window", focus_window, "--clearmodifiers", "ctrl+v"],
                check=True,
            )
        else:
            return False
        return True
    except Exception:
        return False


class State(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()
    DONE = auto()
    ERROR = auto()


_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

_BG = "#1c1c1e"
_SURFACE = "#2c2c2e"
_BORDER = "#3a3a3c"
_TEXT = "#ffffff"
_MUTED = "#aeaeb2"
_RED = "#ff453a"
_RED_DIM = "#7a1f1c"
_YELLOW = "#ffd60a"
_GREEN = "#32d74b"
_GRAY = "#636366"

_STYLE = f"""
QFrame#container {{
    background-color: {_BG};
    border-radius: 12px;
    border: 1px solid {_BORDER};
}}
QWidget#header {{
    background-color: {_SURFACE};
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}}
QLabel#title {{
    color: {_TEXT};
    font-size: 13px;
    font-weight: bold;
}}
QLabel#dot {{
    font-size: 11px;
    color: {_GRAY};
}}
QLabel#timer {{
    color: {_MUTED};
    font-size: 11px;
    font-family: monospace;
    min-width: 32px;
}}
QPushButton#closeBtn {{
    background: transparent;
    color: {_MUTED};
    border: none;
    font-size: 17px;
    padding: 0;
}}
QPushButton#closeBtn:hover {{
    color: {_TEXT};
}}
QWidget#statusArea {{
    background-color: {_BG};
}}
QLabel#status {{
    color: {_TEXT};
    font-size: 12px;
}}
QFrame#divider {{
    background-color: {_BORDER};
    border: none;
    max-height: 1px;
}}
QPushButton#actionBtn {{
    background-color: {_SURFACE};
    color: {_TEXT};
    border: none;
    font-size: 13px;
    font-weight: 600;
    border-bottom-left-radius: 12px;
    border-bottom-right-radius: 12px;
}}
QPushButton#actionBtn:hover:enabled {{
    background-color: #3a3a3c;
}}
QPushButton#actionBtn:disabled {{
    color: {_MUTED};
}}
"""

_BTN_RECORD_STYLE = f"""
QPushButton#actionBtn {{
    background-color: {_RED};
    color: white;
    border: none;
    font-size: 13px;
    font-weight: 600;
    border-bottom-left-radius: 12px;
    border-bottom-right-radius: 12px;
}}
QPushButton#actionBtn:hover {{
    background-color: #ff6b63;
}}
"""


class RecordWorker(QThread):
    finished = Signal(object)      # emits Path
    error_occurred = Signal(str)

    def __init__(self, output_path: Path, cfg: DictationConfig) -> None:
        super().__init__()
        self._output_path = output_path
        self._cfg = cfg
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        try:
            from .audio_capture import record_wav_until_stop
            record_wav_until_stop(
                self._output_path,
                stop_event=self._stop_event,
                max_seconds=self._cfg.max_record_seconds,
                sample_rate=self._cfg.sample_rate,
                channels=self._cfg.channels,
            )
            self.finished.emit(self._output_path)
        except Exception as exc:
            self.error_occurred.emit(str(exc))


class TranscribeWorker(QThread):
    result = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, audio_path: Path, cfg: DictationConfig) -> None:
        super().__init__()
        self._audio_path = audio_path
        self._cfg = cfg

    def run(self) -> None:
        try:
            from .cleanup import cleanup_dictation_text
            from .transcriber import FasterWhisperTranscriber
            tr = FasterWhisperTranscriber(self._cfg)
            transcript = tr.transcribe_file(self._audio_path)
            text = cleanup_dictation_text(transcript.text, append_space=self._cfg.append_space)
            self.result.emit(text)
        except Exception as exc:
            self.error_occurred.emit(str(exc))


class DictationWidget(QWidget):
    def __init__(self, cfg: DictationConfig) -> None:
        super().__init__()
        self._cfg = cfg
        self._state = State.IDLE
        self._drag_pos: QPoint | None = None
        self._record_worker: RecordWorker | None = None
        self._transcribe_worker: TranscribeWorker | None = None
        self._tmpdir: tempfile.TemporaryDirectory | None = None  # type: ignore[type-arg]
        self._elapsed = 0.0
        self._spinner_frame = 0
        self._dot_bright = True
        self._last_text = ""
        self._last_error = ""
        self._focus_window: str | None = None   # VTE child / actual key-event target
        self._class_window: str | None = None   # top-level WM window for class detection

        self._setup_window()
        self._build_ui()
        self._setup_timers()
        self._update_ui()

    def _setup_window(self) -> None:
        self.setWindowTitle("Athena Dictate")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(264, 118)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._container = QFrame()
        self._container.setObjectName("container")
        self._container.setStyleSheet(_STYLE)
        outer.addWidget(self._container)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self._header = QWidget()
        self._header.setObjectName("header")
        self._header.setFixedHeight(32)
        self._header.installEventFilter(self)
        hl = QHBoxLayout(self._header)
        hl.setContentsMargins(12, 0, 10, 0)
        hl.setSpacing(6)

        self._dot_label = QLabel("●")
        self._dot_label.setObjectName("dot")
        self._dot_label.setFixedWidth(13)
        hl.addWidget(self._dot_label)

        title = QLabel("Athena Dictate")
        title.setObjectName("title")
        hl.addWidget(title)
        hl.addStretch()

        self._timer_label = QLabel("")
        self._timer_label.setObjectName("timer")
        hl.addWidget(self._timer_label)

        close_btn = QPushButton("×")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(20, 20)
        close_btn.clicked.connect(self.close)
        hl.addWidget(close_btn)

        layout.addWidget(self._header)

        # Divider
        div1 = QFrame()
        div1.setObjectName("divider")
        div1.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(div1)

        # Status area
        status_area = QWidget()
        status_area.setObjectName("statusArea")
        status_area.installEventFilter(self)
        sl = QHBoxLayout(status_area)
        sl.setContentsMargins(14, 0, 14, 0)

        self._status_label = QLabel()
        self._status_label.setObjectName("status")
        self._status_label.setWordWrap(True)
        sl.addWidget(self._status_label)

        layout.addWidget(status_area, 1)

        # Divider
        div2 = QFrame()
        div2.setObjectName("divider")
        div2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(div2)

        # Action button
        self._action_btn = QPushButton()
        self._action_btn.setObjectName("actionBtn")
        self._action_btn.setFixedHeight(38)
        self._action_btn.clicked.connect(self._on_action)
        layout.addWidget(self._action_btn)

    def _setup_timers(self) -> None:
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._on_pulse)

        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.timeout.connect(self._on_elapsed_tick)

        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(lambda: self._set_state(State.IDLE))

    def _update_ui(self) -> None:
        s = self._state

        if s == State.RECORDING:
            dot_color = _RED if self._dot_bright else _RED_DIM
        elif s == State.TRANSCRIBING:
            dot_color = _YELLOW if self._dot_bright else "#7a6200"
        elif s == State.DONE:
            dot_color = _GREEN
        elif s == State.ERROR:
            dot_color = _RED
        else:
            dot_color = _GRAY

        self._dot_label.setStyleSheet(f"color: {dot_color};")

        spinner = _SPINNER[self._spinner_frame % len(_SPINNER)]

        if s == State.IDLE:
            self._status_label.setText("Ready — click below to dictate")
            self._status_label.setStyleSheet(f"color: {_MUTED}; font-size: 12px;")
        elif s == State.RECORDING:
            self._status_label.setText(f"{spinner}  Recording · click Stop to finish")
            self._status_label.setStyleSheet(f"color: {_TEXT}; font-size: 12px;")
        elif s == State.TRANSCRIBING:
            self._status_label.setText(f"{spinner}  Transcribing...")
            self._status_label.setStyleSheet(f"color: {_MUTED}; font-size: 12px;")
        elif s == State.DONE:
            text = self._last_text
            display = (text[:36] + "…") if len(text) > 38 else text
            self._status_label.setText(f'✓  "{display}"')
            self._status_label.setStyleSheet(f"color: {_GREEN}; font-size: 12px;")
        elif s == State.ERROR:
            msg = self._last_error[:55]
            self._status_label.setText(f"✗  {msg}")
            self._status_label.setStyleSheet(f"color: {_RED}; font-size: 11px;")

        if s == State.RECORDING:
            elapsed_int = int(self._elapsed)
            self._timer_label.setText(f"{elapsed_int // 60:01d}:{elapsed_int % 60:02d}")
        else:
            self._timer_label.setText("")

        if s == State.IDLE:
            self._action_btn.setText("▶   Start Recording")
            self._action_btn.setEnabled(True)
            self._action_btn.setStyleSheet("")
        elif s == State.RECORDING:
            self._action_btn.setText("■   Stop")
            self._action_btn.setEnabled(True)
            self._action_btn.setStyleSheet(_BTN_RECORD_STYLE)
        elif s == State.TRANSCRIBING:
            self._action_btn.setText("◌   Transcribing…")
            self._action_btn.setEnabled(False)
            self._action_btn.setStyleSheet("")
        elif s == State.DONE:
            self._action_btn.setText("▶   Record Again")
            self._action_btn.setEnabled(True)
            self._action_btn.setStyleSheet("")
        elif s == State.ERROR:
            self._action_btn.setText("▶   Try Again")
            self._action_btn.setEnabled(True)
            self._action_btn.setStyleSheet("")

    def _set_state(self, state: State, **kwargs: object) -> None:
        self._state = state
        if "text" in kwargs:
            self._last_text = str(kwargs["text"])
        if "error" in kwargs:
            self._last_error = str(kwargs["error"])

        self._pulse_timer.stop()
        self._elapsed_timer.stop()
        self._reset_timer.stop()

        if state == State.RECORDING:
            self._elapsed = 0.0
            self._spinner_frame = 0
            self._dot_bright = True
            self._pulse_timer.start(450)
            self._elapsed_timer.start(100)
        elif state == State.TRANSCRIBING:
            self._spinner_frame = 0
            self._dot_bright = True
            self._pulse_timer.start(80)
        elif state in (State.DONE, State.ERROR):
            self._reset_timer.start(3500)

        self._update_ui()

    def _on_pulse(self) -> None:
        self._dot_bright = not self._dot_bright
        self._spinner_frame += 1
        self._update_ui()

    def _on_elapsed_tick(self) -> None:
        self._elapsed += 0.1
        self._update_ui()

    def _on_action(self) -> None:
        if self._state in (State.IDLE, State.DONE, State.ERROR):
            self._start_recording()
        elif self._state == State.RECORDING:
            self._stop_recording()

    def _start_recording(self) -> None:
        self._last_text = ""
        self._last_error = ""
        self._focus_window, self._class_window = _capture_target()
        self._tmpdir = tempfile.TemporaryDirectory(prefix="athena-dictate-")
        audio_path = Path(self._tmpdir.name) / "recording.wav"

        self._record_worker = RecordWorker(audio_path, self._cfg)
        self._record_worker.finished.connect(self._on_recording_done)
        self._record_worker.error_occurred.connect(self._on_error)
        self._record_worker.start()
        self._set_state(State.RECORDING)

    def _stop_recording(self) -> None:
        if self._record_worker is not None:
            self._record_worker.stop()

    def _on_recording_done(self, audio_path: object) -> None:
        path = Path(str(audio_path))
        self._set_state(State.TRANSCRIBING)
        self._transcribe_worker = TranscribeWorker(path, self._cfg)
        self._transcribe_worker.result.connect(self._on_transcription_done)
        self._transcribe_worker.error_occurred.connect(self._on_error)
        self._transcribe_worker.start()

    def _on_transcription_done(self, text: str) -> None:
        if text:
            try:
                from .inject import select_injector
                if self._cfg.insertion_backend != "auto":
                    select_injector(self._cfg.insertion_backend).inject(text)
                elif not _x11_paste(text, self._focus_window, self._class_window):
                    select_injector(self._cfg.insertion_backend).inject(text)
            except Exception:
                pass
        self._cleanup_tmpdir()
        self._set_state(State.DONE, text=text or "(no speech detected)")

    def _on_error(self, message: str) -> None:
        self._cleanup_tmpdir()
        self._set_state(State.ERROR, error=message)

    def _cleanup_tmpdir(self) -> None:
        if self._tmpdir is not None:
            try:
                self._tmpdir.cleanup()
            except Exception:
                pass
            self._tmpdir = None

    def closeEvent(self, event) -> None:
        if self._record_worker is not None:
            self._record_worker.stop()
            self._record_worker.wait(2000)
        if self._transcribe_worker is not None:
            self._transcribe_worker.wait(5000)
        self._cleanup_tmpdir()
        super().closeEvent(event)

    # Drag support via eventFilter on header and status area
    def eventFilter(self, obj: object, event: object) -> bool:
        if not isinstance(event, QEvent):
            return super().eventFilter(obj, event)  # type: ignore[arg-type]
        t = event.type()
        if t == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:  # type: ignore[attr-defined]
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()  # type: ignore[attr-defined]
        elif t == QEvent.Type.MouseMove:
            if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:  # type: ignore[attr-defined]
                self.move(event.globalPosition().toPoint() - self._drag_pos)  # type: ignore[attr-defined]
        elif t == QEvent.Type.MouseButtonRelease:
            self._drag_pos = None
        return super().eventFilter(obj, event)  # type: ignore[arg-type]


def launch_widget(cfg: DictationConfig) -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Athena Dictate")
    app.setQuitOnLastWindowClosed(True)

    widget = DictationWidget(cfg)
    # Position near top-right of primary screen
    screen = app.primaryScreen()
    if screen is not None:
        geom = screen.availableGeometry()
        widget.move(geom.right() - widget.width() - 24, geom.top() + 48)

    widget.show()
    sys.exit(app.exec())
