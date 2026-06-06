from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DictationConfig:
    backend: str = "faster_whisper"
    model: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    groq_model: str = "whisper-large-v3-turbo"
    groq_api_key_env: str = "GROQ_API_KEY"
    language: str = "auto"
    multilingual: bool = False
    task: str = "transcribe"
    sample_rate: int = 16_000
    channels: int = 1
    max_record_seconds: float = 0.0
    beam_size: int = 1
    vad_filter: bool = True
    word_timestamps: bool = False
    insertion_backend: str = "auto"
    append_space: bool = True

    @classmethod
    def from_file(cls, path: str | Path | None) -> "DictationConfig":
        if path is None:
            return cls.from_default_locations()
        config_path = Path(path).expanduser()
        if not config_path.exists():
            raise FileNotFoundError(config_path)
        return cls.from_mapping(tomllib.loads(config_path.read_text()))

    @classmethod
    def from_default_locations(cls) -> "DictationConfig":
        candidates = [
            Path.cwd() / "athena-dictate.toml",
            Path.home() / ".config" / "athena-dictate" / "config.toml",
        ]
        for candidate in candidates:
            if candidate.exists():
                return cls.from_file(candidate)
        return cls()

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "DictationConfig":
        allowed = set(cls.__dataclass_fields__)
        values = {key: value for key, value in data.items() if key in allowed}
        return cls(**values)

    def with_env_overrides(self) -> "DictationConfig":
        mapping: dict[str, tuple[str, type]] = {
            "ATHENA_DICTATE_BACKEND": ("backend", str),
            "ATHENA_DICTATE_MODEL": ("model", str),
            "ATHENA_DICTATE_DEVICE": ("device", str),
            "ATHENA_DICTATE_COMPUTE_TYPE": ("compute_type", str),
            "ATHENA_DICTATE_GROQ_MODEL": ("groq_model", str),
            "ATHENA_DICTATE_LANGUAGE": ("language", str),
            "ATHENA_DICTATE_MULTILINGUAL": ("multilingual", _parse_bool),
            "ATHENA_DICTATE_TASK": ("task", str),
            "ATHENA_DICTATE_INSERTION_BACKEND": ("insertion_backend", str),
            "ATHENA_DICTATE_MAX_RECORD_SECONDS": ("max_record_seconds", float),
            "ATHENA_DICTATE_BEAM_SIZE": ("beam_size", int),
        }
        updates: dict[str, object] = {}
        for env_name, (field_name, caster) in mapping.items():
            value = os.getenv(env_name)
            if value:
                updates[field_name] = caster(value)
        return replace(self, **updates)


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value!r}")
