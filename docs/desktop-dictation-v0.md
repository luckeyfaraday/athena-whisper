# Athena Desktop Dictation v0

This project is a desktop speech-input prototype for Athena. The v0 goal is not
batch transcription; it is a small Linux dictation command that records the
microphone, transcribes locally with faster-whisper, cleans the text, and inserts
it into the currently focused text field.

## v0 Workflow

1. Focus a text box in any desktop app.
2. Run `athena-dictate record-once --seconds 5 --paste`.
3. Speak while recording.
4. The command transcribes the WAV with faster-whisper.
5. The cleaned transcript is copied/pasted or copied to the clipboard.

The initial workflow supports either a fixed duration with `--seconds` or a
terminal toggle: press Enter to start, speak, then press Enter to stop. A later
UI can provide push-to-talk press/release, a tray icon, or a global hotkey.

## Defaults

- Model: `base.en`
- Device: `cpu`
- Compute type: `int8`
- Audio: 16 kHz mono WAV
- Maximum recording: no hard cap by default
- Insertion backend: `auto`

These defaults favor a CPU-only laptop. If latency is too high, try `tiny.en`.
If quality is too low and latency is acceptable, try `small.en`.

## Linux Insertion Backends

### X11

The preferred v0 path is clipboard plus `xdotool key ctrl+v`. This is usually
more reliable for multi-word and Unicode text than synthetic key typing.

For terminal apps such as Codex, Claude Code, and shells, use
`x11-terminal-paste`. Those TUIs may treat `Ctrl+V` as an image paste shortcut;
the terminal emulator text paste shortcut is normally `Ctrl+Shift+V`.
If `Ctrl+Shift+V` is still passed through, try
`x11-terminal-shift-insert-paste`. If paste shortcuts are intercepted entirely,
use `x11-keystrokes`, which sends keystrokes instead of using the clipboard.

Install:

```bash
sudo apt-get install xdotool xclip
```

If clipboard paste is unavailable, direct typing with `xdotool type` can be used
as a fallback.

### Wayland

Wayland intentionally restricts global input automation. Options vary by
compositor:

- `wl-copy` from `wl-clipboard` can set clipboard contents.
- `wtype` can simulate keyboard input only on compositors that support the
  virtual-keyboard protocol.
- `ydotool` uses `/dev/uinput`, works below the display server, and requires
  `ydotoold` plus permission to access `/dev/uinput`.

These tools have meaningful security implications because they can inject text
or key events into arbitrary applications.

## Configuration

Create `athena-dictate.toml` in this repo or
`~/.config/athena-dictate/config.toml`:

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

Set `max_record_seconds = 0` to record until the user stops manually. This is
the default. Set a positive value only when you want a hard cap.

Environment overrides:

- `ATHENA_DICTATE_MODEL`
- `ATHENA_DICTATE_DEVICE`
- `ATHENA_DICTATE_COMPUTE_TYPE`
- `ATHENA_DICTATE_LANGUAGE`
- `ATHENA_DICTATE_INSERTION_BACKEND`
- `ATHENA_DICTATE_MAX_RECORD_SECONDS`

## Next Steps

- Add true press/release push-to-talk recording.
- Add a tray/widget process with visible recording/transcribing states.
- Add desktop hotkey setup notes per environment.
- Add optional command phrases such as "scratch that" and "select last word".
- Benchmark `tiny.en`, `base.en`, and `small.en` on Alan's target machine.
