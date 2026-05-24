from athena_whisper_topic.config import DictationConfig


def test_config_defaults_match_v0_target() -> None:
    config = DictationConfig()
    assert config.model == "base.en"
    assert config.device == "cpu"
    assert config.compute_type == "int8"
    assert config.sample_rate == 16_000
    assert config.channels == 1
    assert config.max_record_seconds == 0.0
    assert config.insertion_backend == "auto"


def test_config_from_mapping_ignores_unknown_keys() -> None:
    config = DictationConfig.from_mapping({"model": "tiny.en", "unknown": "ignored"})
    assert config.model == "tiny.en"
