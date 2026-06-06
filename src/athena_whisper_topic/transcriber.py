from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .config import DictationConfig
from .types import TranscriptResult, TranscriptSegment, Word


class Transcriber(Protocol):
    def transcribe_file(self, audio_path: str | Path) -> TranscriptResult: ...


def create_transcriber(config: DictationConfig) -> Transcriber:
    """Return the transcriber implementation selected by ``config.backend``."""
    backend = config.backend.strip().lower()
    if backend in {"faster_whisper", "faster-whisper", "", "local"}:
        return FasterWhisperTranscriber(config)
    if backend == "groq":
        return GroqTranscriber(config)
    raise ValueError(f"unknown transcription backend: {config.backend!r}")


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


@dataclass
class GroqTranscriber:
    config: DictationConfig
    _client: Any | None = None

    @property
    def client(self) -> Any:
        if self._client is None:
            from groq import Groq

            api_key = os.getenv(self.config.groq_api_key_env)
            if not api_key:
                raise RuntimeError(
                    f"Groq API key not found; set the {self.config.groq_api_key_env} "
                    "environment variable."
                )
            self._client = Groq(api_key=api_key)
        return self._client

    def transcribe_file(self, audio_path: str | Path) -> TranscriptResult:
        audio_path = Path(audio_path)
        language = self.config.language.strip()
        detect = not language or language.lower() == "auto"
        audio_bytes = audio_path.read_bytes()

        if self.config.task == "translate":
            # The translation endpoint always outputs English and takes no language.
            response = self.client.audio.translations.create(
                file=(audio_path.name, audio_bytes),
                model=self.config.groq_model,
                response_format="verbose_json",
            )
        else:
            response = self.client.audio.transcriptions.create(
                file=(audio_path.name, audio_bytes),
                model=self.config.groq_model,
                language=None if detect else language,
                response_format="verbose_json",
            )
        return build_transcript_result_from_groq(response)


def build_transcript_result_from_groq(response: Any) -> TranscriptResult:
    raw_segments = _groq_attr(response, "segments") or ()
    segments: list[TranscriptSegment] = []
    for raw in raw_segments:
        start = _groq_attr(raw, "start")
        end = _groq_attr(raw, "end")
        segments.append(
            TranscriptSegment(
                start=float(start) if start is not None else 0.0,
                end=float(end) if end is not None else 0.0,
                text=str(_groq_attr(raw, "text") or "").strip(),
            )
        )

    full_text = _groq_attr(response, "text")
    if full_text is not None:
        text = str(full_text).strip()
    else:
        text = " ".join(segment.text for segment in segments).strip()

    return TranscriptResult(
        text=text,
        language=_groq_attr(response, "language"),
        language_probability=None,
        duration=_groq_attr(response, "duration"),
        segments=tuple(segments),
    )


def _groq_attr(obj: Any, name: str) -> Any:
    """Read ``name`` from a Groq response that may be an object or a dict."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)
