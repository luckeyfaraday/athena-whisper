from athena_whisper_topic.config import DictationConfig


def test_config_defaults_match_v0_target() -> None:
    config = DictationConfig()
    assert config.model == "base"
    assert config.device == "cpu"
    assert config.compute_type == "int8"
    assert config.language == "auto"
    assert config.multilingual is False
    assert config.task == "transcribe"
    assert config.sample_rate == 16_000
    assert config.channels == 1
    assert config.max_record_seconds == 0.0
    assert config.insertion_backend == "auto"


def test_config_from_mapping_ignores_unknown_keys() -> None:
    config = DictationConfig.from_mapping({"model": "tiny.en", "unknown": "ignored"})
    assert config.model == "tiny.en"


def test_config_reads_multilingual_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("ATHENA_DICTATE_LANGUAGE", "es")
    monkeypatch.setenv("ATHENA_DICTATE_MULTILINGUAL", "true")
    monkeypatch.setenv("ATHENA_DICTATE_TASK", "translate")

    config = DictationConfig().with_env_overrides()

    assert config.language == "es"
    assert config.multilingual is True
    assert config.task == "translate"
