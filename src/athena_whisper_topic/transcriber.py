from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import DictationConfig
from .types import TranscriptResult, TranscriptSegment, Word


@dataclass
class FasterWhisperTranscriber:
    config: DictationConfig
    _model: Any | None = None

    @property
    def model(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.config.model,
                device=self.config.device,
                compute_type=self.config.compute_type,
            )
        return self._model

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
