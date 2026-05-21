from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RecordingInfo:
    path: Path
    seconds: float
    sample_rate: int
    channels: int


def record_wav(
    output_path: str | Path,
    seconds: float,
    sample_rate: int = 16_000,
    channels: int = 1,
) -> RecordingInfo:
    """Record microphone audio to a WAV file.

    Imports are local so the rest of the package remains usable before audio
    dependencies are installed or when no sound device is present.
    """
    import sounddevice as sd
    import soundfile as sf

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(seconds * sample_rate)
    audio = sd.rec(frames, samplerate=sample_rate, channels=channels, dtype="float32")
    sd.wait()
    sf.write(path, audio, sample_rate)
    return RecordingInfo(path=path, seconds=seconds, sample_rate=sample_rate, channels=channels)


def record_wav_until_stop(
    output_path: str | Path,
    stop_event: threading.Event,
    max_seconds: float,
    sample_rate: int = 16_000,
    channels: int = 1,
) -> RecordingInfo:
    """Record microphone audio until an event is set or max_seconds is reached."""
    import numpy as np
    import sounddevice as sd
    import soundfile as sf

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    chunks = []
    started_at = time.monotonic()

    def callback(indata, frames, time_info, status) -> None:  # noqa: ANN001
        del frames, time_info, status
        chunks.append(indata.copy())

    with sd.InputStream(samplerate=sample_rate, channels=channels, dtype="float32", callback=callback):
        while not stop_event.is_set() and time.monotonic() - started_at < max_seconds:
            time.sleep(0.05)

    seconds = time.monotonic() - started_at
    audio = np.concatenate(chunks, axis=0) if chunks else np.zeros((0, channels), dtype="float32")
    sf.write(path, audio, sample_rate)
    return RecordingInfo(path=path, seconds=seconds, sample_rate=sample_rate, channels=channels)
