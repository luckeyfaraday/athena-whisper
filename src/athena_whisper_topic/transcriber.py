from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import DictationConfig
from .types import TranscriptResult, TranscriptSegment, Word


@dataclass
class FasterWhisperTranscriber:
    config: DictationConfig
    _model: Any | None = None
    _model_lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False
    )

    @property
    def model(self) -> Any:
        # Double-checked locking: the model is loaded once and reused for every
        # transcription. Without the lock a warm-up thread and a transcription
        # thread could both observe ``_model is None`` and load it twice.
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    from faster_whisper import WhisperModel

                    self._model = WhisperModel(
                        self.config.model,
                        device=self.config.device,
                        compute_type=self.config.compute_type,
                    )
        return self._model

    def warm_up(self) -> None:
        """Load the model and exercise the decode/VAD paths ahead of time.

        Running a short silent buffer through ``transcribe`` forces the model,
        feature extractor, and (when enabled) the VAD model to load, so the
        first real dictation does not pay that one-time cost. Safe to call from
        a background thread; failures are swallowed because warm-up is purely an
        optimization.
        """
        try:
            import numpy as np

            silence = np.zeros(self.config.sample_rate, dtype="float32")
            segments_iter, _info = self.model.transcribe(
                silence,
                beam_size=self.config.beam_size,
                vad_filter=self.config.vad_filter,
            )
            for _ in segments_iter:
                pass
        except Exception:
            pass

    def transcribe_file(self, audio_path: str | Path) -> TranscriptResult:
        language = self.config.language.strip()
        segments_iter, info = self.model.transcribe(
            str(audio_path),
            beam_size=self.config.beam_size,
            language=None if not language or language.lower() == "auto" else language,
            multilingual=self.config.multilingual,
            task=self.config.task,
            vad_filter=self.config.vad_filter,
            word_timestamps=self.config.word_timestamps,
        )
        return build_transcript_result(segments_iter, info)


def build_transcript_result(segments_iter: Any, info: Any) -> TranscriptResult:
    segments: list[TranscriptSegment] = []
    for segment in segments_iter:
        words = tuple(
            Word(start=float(word.start), end=float(word.end), word=str(word.word))
            for word in (getattr(segment, "words", None) or ())
        )
        segments.append(
            TranscriptSegment(
                start=float(segment.start),
                end=float(segment.end),
                text=str(segment.text).strip(),
                words=words,
            )
        )

    text = " ".join(segment.text for segment in segments).strip()
    return TranscriptResult(
        text=text,
        language=getattr(info, "language", None),
        language_probability=getattr(info, "language_probability", None),
        duration=getattr(info, "duration", None),
        segments=tuple(segments),
    )
