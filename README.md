# Athena Whisper Topic

Desktop dictation prototype for Athena.

The v0 target is a Linux speech-input command/widget: activate it, speak into
the microphone, transcribe locally with `faster-whisper`, clean the result, and
insert the text into the currently focused text box.

## Setup

Create a virtual environment and install the package:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

For X11 paste insertion, install desktop tools:

```bash
sudo apt-get install xdotool xclip
```

Wayland support depends on the compositor. See
[`docs/desktop-dictation-v0.md`](docs/desktop-dictation-v0.md).

## Usage

Check the local desktop/session environment:

```bash
athena-dictate doctor
```

Transcribe an existing audio file:

```bash
athena-dictate transcribe-file path/to/audio.wav
```

Record five seconds, transcribe, and paste into the focused field:

```bash
athena-dictate record-once --seconds 5 --paste
```

For terminal apps such as Codex, Claude Code, and shells, use terminal paste.
These apps often treat `Ctrl+V` as an image-paste command, while terminal
emulators usually paste text with `Ctrl+Shift+V`:

```bash
athena-dictate record-once --seconds 5 --paste --insertion-backend x11-terminal-paste
```

If that still reaches the app as image paste, try `Shift+Insert` paste:

```bash
athena-dictate record-once --seconds 5 --paste --insertion-backend x11-terminal-shift-insert-paste
```

If both paste shortcuts are intercepted, use keystrokes, which avoids the
clipboard entirely:

```bash
athena-dictate record-once --seconds 5 --paste --insertion-backend x11-keystrokes
```

Test insertion without recording:

```bash
athena-dictate type-text "hello from athena"
```

`type-text` is intentionally hardcoded to keystrokes. It never uses the
clipboard and never sends a paste shortcut.

Record without inserting:

```bash
athena-dictate record-once --seconds 5 --no-paste
```

## Defaults

- Model: `base.en`
- Device: `cpu`
- Compute type: `int8`
- Audio: 16 kHz mono
- Max recording: 30 seconds
- Insertion backend: `auto`

Create `athena-dictate.toml` in this repo to override defaults:

```toml
model = "base.en"
device = "cpu"
compute_type = "int8"
language = "en"
insertion_backend = "auto"
```

Useful insertion backends:

- `auto`: normal desktop text fields; currently prefers X11 clipboard paste.
- `x11-terminal-paste`: terminal paste using `Ctrl+Shift+V`.
- `x11-terminal-shift-insert-paste`: terminal paste using `Shift+Insert`.
- `x11-keystrokes`: synthetic keystrokes; best for Codex, Claude Code, and shells.
- `x11-direct-type`: older synthetic typing fallback.
- `clipboard-only`: copy transcript and paste manually.

## Development

Run tests:

```bash
pytest
```
