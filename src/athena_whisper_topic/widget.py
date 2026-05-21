from __future__ import annotations

import math
import sys
import tempfile
import threading
from enum import Enum, auto
from pathlib import Path

_ICON_SVG = Path(__file__).parent / "assets" / "athena-app-icon.svg"

from .config import DictationConfig

try:
    from PyQt6.QtCore import QEvent, QPoint, QPointF, QTimer, Qt, QThread, pyqtSignal as Signal
    from PyQt6.QtGui import QColor, QCursor, QIcon, QPainter, QPen
    from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
except ImportError:
    try:
        from PySide6.QtCore import QEvent, QPoint, QPointF, QTimer, Qt, QThread, Signal
        from PySide6.QtGui import QColor, QCursor, QIcon, QPainter, QPen
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


# ── Athena logo widget ────────────────────────────────────────────────────────

class AthenaLogoWidget(QWidget):
    """Paints the Athena 6-line asterisk logo at any size."""

    _INNER_RATIO = 34 / 86  # from SVG geometry

    def __init__(self, size: int = 14, color: str = "#F3EDE3", parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._color = QColor(color)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self._color)
        pen.setWidthF(1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        cx = self.width() / 2
        cy = self.height() / 2
        r_outer = min(self.width(), self.height()) / 2 - 0.5
        r_inner = r_outer * self._INNER_RATIO

        for i in range(6):
            angle = math.radians(90 + 60 * i)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            painter.drawLine(
                QPointF(cx + r_inner * cos_a, cy - r_inner * sin_a),
                QPointF(cx + r_outer * cos_a, cy - r_outer * sin_a),
            )
        painter.end()


# ── States ────────────────────────────────────────────────────────────────────

class State(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()
    DONE = auto()
    ERROR = auto()


# ── Design tokens ─────────────────────────────────────────────────────────────

_BG       = "#0a0a0c"
_HEADER   = "#0f0f12"
_BORDER   = "#1e1e26"
_TEXT     = "#e2e2e8"
_MUTED    = "#4a4a56"
_FONT     = '"JetBrains Mono", "Fira Code", "Cascadia Code", "Liberation Mono", monospace'

_C_IDLE   = "#3a3a46"
_C_REC    = "#ff3355"
_C_REC_DIM= "#7a1428"
_C_PROC   = "#0a84ff"
_C_DONE   = "#30d158"
_C_ERR    = "#ff453a"

_STATE_COLORS: dict[State, str] = {
    State.IDLE:         _C_IDLE,
    State.RECORDING:    _C_REC,
    State.TRANSCRIBING: _C_PROC,
    State.DONE:         _C_DONE,
    State.ERROR:        _C_ERR,
}

# Waveform frames cycled during recording (unicode block chars)
_WAVES = [
    "▁▂▄▆▇▆▄▂▁▃▅▇▅▃",
    "▂▄▆▇▆▄▂▁▂▄▆▇▅▃",
    "▃▅▇▆▄▂▁▂▃▅▇▆▄▂",
    "▄▆▇▅▃▁▁▂▄▆▇▅▃▂",
    "▅▇▆▄▂▁▂▃▅▇▆▄▂▁",
    "▇▆▄▂▁▂▄▅▇▆▄▂▁▂",
    "▆▄▂▁▂▄▆▇▆▄▂▁▂▄",
    "▄▂▁▂▄▆▇▆▄▂▁▃▅▇",
]

_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def _build_style(state_color: str) -> str:
    return f"""
QFrame#container {{
    background-color: {_BG};
    border-radius: 10px;
    border-top: 1px solid {_BORDER};
    border-right: 1px solid {_BORDER};
    border-bottom: 1px solid {_BORDER};
    border-left: 3px solid {state_color};
}}
QWidget#header {{
    background-color: {_HEADER};
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}}
QLabel#brand {{
    color: {_MUTED};
    font-family: {_FONT};
    font-size: 9px;
    font-weight: bold;
    letter-spacing: 3px;
}}
QLabel#brandDot {{
    color: {state_color};
    font-size: 7px;
    padding-right: 4px;
}}
QLabel#timerLabel {{
    color: {state_color};
    font-family: {_FONT};
    font-size: 10px;
    min-width: 34px;
    qproperty-alignment: AlignRight;
}}
QPushButton#closeBtn {{
    background: transparent;
    color: {_MUTED};
    border: none;
    font-size: 15px;
    padding: 0 1px;
    min-width: 18px;
}}
QPushButton#closeBtn:hover {{
    color: {_TEXT};
}}
QWidget#statusArea {{
    background-color: {_BG};
}}
"""


def _btn_style(bg: str, fg: str, hover: str, border_top: str = _BORDER) -> str:
    return f"""
QPushButton#actionBtn {{
    background-color: {bg};
    color: {fg};
    border: none;
    font-family: {_FONT};
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 2px;
    border-bottom-left-radius: 10px;
    border-bottom-right-radius: 10px;
    border-top: 1px solid {border_top};
}}
QPushButton#actionBtn:hover:enabled {{
    background-color: {hover};
}}
QPushButton#actionBtn:disabled {{
    color: {_MUTED};
    background-color: {bg};
}}
"""


# ── Worker threads ─────────────────────────────────────────────────────────────

class RecordWorker(QThread):
    finished = Signal(object)
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


# ── Widget ────────────────────────────────────────────────────────────────────

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
        self._focus_window: str | None = None
        self._class_window: str | None = None

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
        self.setFixedSize(268, 118)
        if _ICON_SVG.exists():
            self.setWindowIcon(QIcon(str(_ICON_SVG)))

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._container = QFrame()
        self._container.setObjectName("container")
        outer.addWidget(self._container)

        root = QVBoxLayout(self._container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────
        self._header = QWidget()
        self._header.setObjectName("header")
        self._header.setFixedHeight(28)
        self._header.installEventFilter(self)
        hl = QHBoxLayout(self._header)
        hl.setContentsMargins(10, 0, 8, 0)
        hl.setSpacing(6)
        hl.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._brand_dot = AthenaLogoWidget(size=13)
        hl.addWidget(self._brand_dot, 0, Qt.AlignmentFlag.AlignVCenter)

        brand = QLabel("DICTATE")
        brand.setObjectName("brand")
        hl.addWidget(brand, 0, Qt.AlignmentFlag.AlignVCenter)

        hl.addStretch()

        self._timer_label = QLabel("")
        self._timer_label.setObjectName("timerLabel")
        hl.addWidget(self._timer_label)

        close_btn = QPushButton("×")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(20, 20)
        close_btn.clicked.connect(self.close)
        hl.addWidget(close_btn)

        root.addWidget(self._header)

        # ── Status area ─────────────────────────────────────────────
        status_area = QWidget()
        status_area.setObjectName("statusArea")
        status_area.installEventFilter(self)
        sl = QVBoxLayout(status_area)
        sl.setContentsMargins(12, 0, 12, 0)
        sl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._status_label = QLabel()
        self._status_label.setObjectName("statusLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setWordWrap(False)
        sl.addWidget(self._status_label)

        root.addWidget(status_area, 1)

        # ── Action button ────────────────────────────────────────────
        self._action_btn = QPushButton()
        self._action_btn.setObjectName("actionBtn")
        self._action_btn.setFixedHeight(40)
        self._action_btn.clicked.connect(self._on_action)
        root.addWidget(self._action_btn)

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
        sc = _STATE_COLORS[s]

        # Container border color
        self._container.setStyleSheet(_build_style(sc))

        # Header logo — stays cream; state is already signalled by the left stripe

        # Timer
        if s == State.RECORDING:
            t = int(self._elapsed)
            self._timer_label.setText(f"{t // 60:01d}:{t % 60:02d}")
            self._timer_label.setStyleSheet(f"color: {sc}; font-family: {_FONT}; font-size: 10px; min-width: 34px;")
        else:
            self._timer_label.setText("")

        # Status label
        if s == State.IDLE:
            self._status_label.setText("—  READY  —")
            self._status_label.setStyleSheet(
                f"color: {_MUTED}; font-family: {_FONT}; font-size: 10px; letter-spacing: 3px;"
            )
        elif s == State.RECORDING:
            wave = _WAVES[self._spinner_frame % len(_WAVES)]
            wave_color = sc if self._dot_bright else _C_REC_DIM
            self._status_label.setText(wave)
            self._status_label.setStyleSheet(
                f"color: {wave_color}; font-family: {_FONT}; font-size: 14px; letter-spacing: 1px;"
            )
        elif s == State.TRANSCRIBING:
            sp = _SPINNER[self._spinner_frame % len(_SPINNER)]
            self._status_label.setText(f"{sp}  PROCESSING")
            self._status_label.setStyleSheet(
                f"color: {sc}; font-family: {_FONT}; font-size: 10px; letter-spacing: 3px;"
            )
        elif s == State.DONE:
            raw = self._last_text
            display = (raw[:30] + "…") if len(raw) > 32 else raw
            self._status_label.setText(f"✓  {display}")
            self._status_label.setStyleSheet(
                f"color: {sc}; font-family: {_FONT}; font-size: 11px;"
            )
        elif s == State.ERROR:
            self._status_label.setText(f"✕  {self._last_error[:38]}")
            self._status_label.setStyleSheet(
                f"color: {sc}; font-family: {_FONT}; font-size: 10px;"
            )

        # Action button
        if s == State.IDLE:
            self._action_btn.setText("▶  START RECORDING")
            self._action_btn.setEnabled(True)
            self._action_btn.setStyleSheet(
                _btn_style("#141418", _TEXT, "#1c1c22")
            )
        elif s == State.RECORDING:
            self._action_btn.setText("■  STOP")
            self._action_btn.setEnabled(True)
            self._action_btn.setStyleSheet(
                _btn_style(_C_REC, "#ffffff", "#ff5577", border_top=_C_REC)
            )
        elif s == State.TRANSCRIBING:
            self._action_btn.setText("◌  TRANSCRIBING")
            self._action_btn.setEnabled(False)
            self._action_btn.setStyleSheet(
                _btn_style("#0d1219", sc, "#0d1219")
            )
        elif s == State.DONE:
            self._action_btn.setText("▶  RECORD AGAIN")
            self._action_btn.setEnabled(True)
            self._action_btn.setStyleSheet(
                _btn_style("#091610", sc, "#0e2018", border_top="#1a3d28")
            )
        elif s == State.ERROR:
            self._action_btn.setText("▶  TRY AGAIN")
            self._action_btn.setEnabled(True)
            self._action_btn.setStyleSheet(
                _btn_style("#120909", sc, "#1f1010", border_top="#3a1a1a")
            )

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
            self._pulse_timer.start(120)
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
                if not _x11_paste(text, self._focus_window, self._class_window):
                    from .inject import select_injector
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
    if _ICON_SVG.exists():
        app.setWindowIcon(QIcon(str(_ICON_SVG)))

    widget = DictationWidget(cfg)
    screen = app.primaryScreen()
    if screen is not None:
        geom = screen.availableGeometry()
        widget.move(geom.right() - widget.width() - 24, geom.top() + 48)

    widget.show()
    sys.exit(app.exec())
