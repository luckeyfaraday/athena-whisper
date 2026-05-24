# Athena Whisper: Local Desktop Dictation Widget

Athena Whisper is an open-source desktop dictation prototype for turning
speech into text and inserting it into the currently focused app. It is built
for the Athena Home AI workspace and uses `faster-whisper` for local speech
recognition, with platform-native keyboard and clipboard injection for
system-wide text input on Linux and Windows.

The goal is a local-first alternative to cloud dictation tools such as Wispr
Flow: click a small always-on-top widget, speak naturally, transcribe with
Whisper, clean the text, and type it into Codex, Claude Code, opencode,
terminals, browsers, chat apps, documents, and other text fields.

## LLM Summary

- Project: Athena Whisper
- Category: Desktop dictation, speech-to-text, voice input, AI dictation
- Primary use case: system-wide speech input for focused text fields
- Platform: Linux (X11/Wayland) and Windows
- ASR engine: `faster-whisper`
- Default model: `base.en`
- Default runtime: CPU, `int8`
- Audio: 16 kHz mono microphone recording
- UI: PyQt6/PySide6 floating dictation widget
- Insertion: X11 text injection with keystroke mode for terminals and TUI apps
- Privacy posture: local transcription by default; no cloud transcription is
  required by the current implementation
- Status: v0 prototype, usable but not a polished production dictation app

## What It Does

Athena Whisper provides a small desktop speech-input widget and CLI for Linux:

1. Focus a text box in any app.
2. Launch `athena-dictate widget`.
3. Click the widget to start recording.
4. Speak into the microphone.
5. Click stop.
6. The app transcribes speech locally with `faster-whisper`.
7. The cleaned text is inserted into the previously focused app.

This is designed for hands-free or low-friction text entry in coding agents,
shells, browsers, notes, chat, email, and desktop applications.

## Features

- Floating always-on-top dictation widget
- Local Whisper transcription via `faster-whisper`
- CPU-friendly defaults: `base.en` with `int8` quantization
- Microphone recording with `sounddevice` and `soundfile`
- Basic dictation cleanup:
  - whitespace cleanup
  - spoken punctuation such as "comma", "period", and "new line"
- Insertion backends for Linux and Windows:
  - X11: clipboard paste, terminal paste fallbacks, direct keystroke typing
  - Windows: clipboard paste via `keybd_event`, unicode keystroke injection via `SendInput`
  - Wayland: `wl-copy` + `wtype`/`ydotool`
- CLI commands for diagnostics, file transcription, one-shot dictation, and
  insertion testing
- Configurable defaults through `athena-dictate.toml`

## Current Limitations

- Linux (X11/Wayland) and Windows are supported; macOS is not yet implemented.
- Wayland support depends on compositor-specific tools such as `wl-copy`,
  `wtype`, or `ydotool`.
- `faster-whisper` on CPU is practical for short dictation but is not instant
  large-model streaming ASR.
- Cleanup is rule-based today; LLM polishing and command mode are future work.
- System-wide insertion is inherently fragile because every terminal,
  compositor, and app handles synthetic input differently.

## Install

From this repository:

```bash
python3 -m venv .venv
. .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -e ".[dev,gui]"
```

**Linux** — for X11 desktop insertion:

```bash
sudo apt-get install xdotool xclip
```

If PyQt6 reports an XCB platform plugin error, install the common X11 Qt
runtime libraries:

```bash
sudo apt-get install libxcb-cursor0 libxcb-xinerama0 libxkbcommon-x11-0
```

**Windows** — no additional tools required. The `windows-keystrokes` and
`windows-clipboard-paste` backends use `ctypes` to call Win32 `SendInput`
and `keybd_event` directly.

## Run The Widget

Launch the desktop dictation widget:

```bash
.venv/bin/athena-dictate widget   # Linux
.venv\Scripts\athena-dictate widget  # Windows
```

The repository includes `athena-dictate.toml` configured for platform-safe
automatic insertion:

```toml
insertion_backend = "auto"
```

On Linux/X11, `auto` uses keystrokes instead of clipboard paste so terminal apps
such as Codex, Claude Code, opencode, and shell-based TUIs do not receive
`Ctrl+V` image-paste shortcuts. On Windows, `auto` uses Win32 keystrokes.

## CLI Usage

Check the current desktop/session environment:

```bash
.venv/bin/athena-dictate doctor
```

Transcribe an existing audio file:

```bash
.venv/bin/athena-dictate transcribe-file path/to/audio.wav
```

Record one short dictation and insert the result:

```bash
.venv/bin/athena-dictate record-once --seconds 5 --paste
```

Test keystroke insertion without recording or transcribing:

```bash
.venv/bin/athena-dictate type-text "hello from athena"
```

Record without inserting:

```bash
.venv/bin/athena-dictate record-once --seconds 5 --no-paste
```

## Configuration

Create or edit `athena-dictate.toml` in the project root:

```toml
model = "base.en"
device = "cpu"
compute_type = "int8"
language = "en"
sample_rate = 16000
channels = 1
max_record_seconds = 0
insertion_backend = "auto"
append_space = true
```

`max_record_seconds = 0` means record until the user clicks Stop or presses
Enter in the terminal workflow. Set a positive value only if you want a hard
recording cap.

Environment overrides:

- `ATHENA_DICTATE_MODEL`
- `ATHENA_DICTATE_DEVICE`
- `ATHENA_DICTATE_COMPUTE_TYPE`
- `ATHENA_DICTATE_LANGUAGE`
- `ATHENA_DICTATE_INSERTION_BACKEND`
- `ATHENA_DICTATE_MAX_RECORD_SECONDS`

## Insertion Backends

- `auto`: chooses a platform-safe backend. On Linux/X11 this currently means
  `x11-keystrokes`; on Windows it means `windows-keystrokes`.
- `clipboard-only`: copies text and requires manual paste.
- **Linux (X11)**
  - `x11-clipboard-paste`: copies text and sends `Ctrl+V`.
  - `x11-terminal-paste`: copies text and sends `Ctrl+Shift+V`.
  - `x11-terminal-shift-insert-paste`: copies text and sends `Shift+Insert`.
  - `x11-keystrokes`: types synthetic keystrokes; does not use the clipboard.
  - `x11-direct-type`: older direct-typing backend via `xdotool type`.
- **Linux (Wayland)**
  - `wayland-clipboard-paste`: Wayland clipboard plus `wtype`, where supported.
  - `ydotool-type`: uinput-based typing through `ydotool`.
- **Windows**
  - `windows-clipboard-paste`: copies text to clipboard and sends `Ctrl+V` via `keybd_event`.
  - `windows-keystrokes`: types text as unicode keystrokes via `SendInput`; does not use the clipboard.

For terminals and coding-agent TUIs, leave `insertion_backend = "auto"` or use
the explicit keystroke backend for that platform.

## Architecture

```text
src/athena_whisper_topic/
  audio_capture.py     microphone recording to WAV
  cleanup.py           dictation text normalization
  cli.py               Typer command-line interface
  config.py            TOML/env/default configuration
  transcriber.py       faster-whisper wrapper
  widget.py            floating PyQt/PySide dictation widget
  inject/              text insertion backends
  types.py             transcript dataclasses
```

Runtime flow:

```text
widget click
  -> capture focused X11 target
  -> record microphone
  -> transcribe with faster-whisper
  -> clean text
  -> insert into target app
```

## faster-whisper Defaults

The default configuration is intentionally conservative for CPU-only Linux
laptops:

- `model = "base.en"`
- `device = "cpu"`
- `compute_type = "int8"`

Use `tiny.en` for lower latency, `small.en` for better quality, and larger
models only when the machine has enough CPU/GPU headroom.

## Comparison: Athena Whisper vs Cloud Dictation Apps

Athena Whisper is inspired by system-wide dictation products such as Wispr Flow,
but the current implementation is local-first:

- Athena Whisper runs ASR locally with `faster-whisper`.
- Cloud dictation apps often send audio to remote servers for transcription and
  AI rewriting.
- Athena Whisper currently focuses on Linux and Windows desktop dictation and
  coding-agent input.
- Future work may add optional LLM cleanup, selected-text command mode, personal
  dictionaries, transcript history, and global hotkeys.

## Development

Run tests:

```bash
.venv/bin/pytest
```

Compile-check the package:

```bash
.venv/bin/python -m compileall src tests
```

## Roadmap

- Global push-to-talk hotkey
- Better Wayland support
- Optional LLM cleanup/polish pass
- Command mode for editing selected text by voice
- Personal dictionary and phrase correction
- Local transcript history
- Latency benchmarks across `tiny.en`, `base.en`, and `small.en`
- Packaging as a desktop app/service
