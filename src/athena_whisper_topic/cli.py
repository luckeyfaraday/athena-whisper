from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from pathlib import Path

import typer

from .audio_capture import record_wav, record_wav_until_stop
from .cleanup import cleanup_dictation_text
from .config import DictationConfig
from .inject import InjectionEnvironment, select_injector
from .inject.x11 import X11KeystrokeInjector
from .transcriber import FasterWhisperTranscriber

app = typer.Typer(help="Athena desktop dictation prototype.")
BACKEND_HELP = (
    "Insertion backend: auto, clipboard-only, x11-clipboard-paste, "
    "x11-terminal-paste, x11-terminal-shift-insert-paste, x11-direct-type, "
    "x11-keystrokes, wayland-clipboard-paste, ydotool-type."
)


def _load_config(config_path: Path | None) -> DictationConfig:
    return DictationConfig.from_file(config_path).with_env_overrides()


@app.command("doctor")
def doctor() -> None:
    """Report desktop/session tools needed for dictation insertion."""
    env = InjectionEnvironment.detect()
    report = {
        "session_type": env.session_type,
        "display": os.getenv("DISPLAY"),
        "wayland_display": os.getenv("WAYLAND_DISPLAY"),
        "tools": {
            "xdotool": shutil.which("xdotool"),
            "wtype": shutil.which("wtype"),
            "ydotool": shutil.which("ydotool"),
            "wl-copy": shutil.which("wl-copy"),
            "xclip": shutil.which("xclip"),
            "xsel": shutil.which("xsel"),
        },
        "selected_injector": select_injector("auto", env).backend_name,
    }
    typer.echo(json.dumps(report, indent=2))


@app.command("transcribe-file")
def transcribe_file(
    audio: Path = typer.Argument(..., exists=True, readable=True),
    config: Path | None = typer.Option(None, "--config", "-c", help="TOML config path."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
    cleanup: bool = typer.Option(True, "--cleanup/--no-cleanup", help="Clean dictation text."),
) -> None:
    """Transcribe an existing audio file."""
    cfg = _load_config(config)
    result = FasterWhisperTranscriber(cfg).transcribe_file(audio)
    text = cleanup_dictation_text(result.text, append_space=False) if cleanup else result.text
    if json_output:
        typer.echo(
            json.dumps(
                {
                    "text": text,
                    "language": result.language,
                    "language_probability": result.language_probability,
                    "duration": result.duration,
                    "segments": [
                        {"start": segment.start, "end": segment.end, "text": segment.text}
                        for segment in result.segments
                    ],
                },
                indent=2,
            )
        )
    else:
        typer.echo(text)


@app.command("insert-text")
def insert_text(
    text: str = typer.Argument(..., help="Text to insert into the currently focused app."),
    insertion_backend: str = typer.Option("auto", "--insertion-backend", help=BACKEND_HELP),
) -> None:
    """Insert literal text without recording or transcribing."""
    injector = select_injector(insertion_backend)
    injection = injector.inject(text)
    typer.echo(f"{injection.backend}: {injection.detail}")


@app.command("type-text")
def type_text(
    text: str = typer.Argument(..., help="Text to type as synthetic X11 keystrokes."),
) -> None:
    """Type literal text with xdotool only; never uses clipboard or paste keys."""
    injection = X11KeystrokeInjector().inject(text)
    typer.echo(f"{injection.backend}: {injection.detail}")


@app.command("record-once")
def record_once(
    seconds: float = typer.Option(0.0, "--seconds", "-s", help="Fixed duration. If 0, prompt before stop."),
    paste: bool = typer.Option(True, "--paste/--no-paste", help="Insert transcript into focused field."),
    insertion_backend: str | None = typer.Option(None, "--insertion-backend", help=BACKEND_HELP),
    config: Path | None = typer.Option(None, "--config", "-c", help="TOML config path."),
    keep_audio: Path | None = typer.Option(None, "--keep-audio", help="Path to save recorded WAV."),
) -> None:
    """Record microphone audio once, transcribe it, and optionally paste the text."""
    cfg = _load_config(config)
    with tempfile.TemporaryDirectory(prefix="athena-dictate-") as tmpdir:
        audio_path = keep_audio or Path(tmpdir) / "recording.wav"

        if seconds <= 0:
            typer.echo("Press Enter to start recording.")
            input()
            typer.echo(f"Recording. Press Enter to stop, or wait {cfg.max_record_seconds:g}s.")
            stop_event = threading.Event()
            worker = threading.Thread(
                target=record_wav_until_stop,
                kwargs={
                    "output_path": audio_path,
                    "stop_event": stop_event,
                    "max_seconds": cfg.max_record_seconds,
                    "sample_rate": cfg.sample_rate,
                    "channels": cfg.channels,
                },
                daemon=True,
            )
            worker.start()
            input()
            stop_event.set()
            worker.join()
        else:
            if seconds > cfg.max_record_seconds:
                raise typer.BadParameter(
                    f"seconds must be <= max_record_seconds ({cfg.max_record_seconds:g})"
                )
            typer.echo(f"Recording {seconds:g}s...")
            record_wav(audio_path, seconds, sample_rate=cfg.sample_rate, channels=cfg.channels)

        typer.echo("Transcribing...")
        result = FasterWhisperTranscriber(cfg).transcribe_file(audio_path)

    text = cleanup_dictation_text(result.text, append_space=cfg.append_space)
    typer.echo(text)
    if paste and text:
        injector = select_injector(insertion_backend or cfg.insertion_backend)
        injection = injector.inject(text)
        typer.echo(f"{injection.backend}: {injection.detail}")


@app.command("widget")
def widget_cmd(
    config: Path | None = typer.Option(None, "--config", "-c", help="TOML config path."),
) -> None:
    """Launch the floating dictation widget."""
    cfg = _load_config(config)
    try:
        from .widget import launch_widget
    except ImportError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)
    launch_widget(cfg)


if __name__ == "__main__":
    app()
