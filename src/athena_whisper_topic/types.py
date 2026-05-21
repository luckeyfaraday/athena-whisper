from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Word:
    start: float
    end: float
    word: str


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    words: tuple[Word, ...] = ()


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    language: str | None = None
    language_probability: float | None = None
    duration: float | None = None
    segments: tuple[TranscriptSegment, ...] = field(default_factory=tuple)
