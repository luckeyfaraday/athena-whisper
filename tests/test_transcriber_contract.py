from types import SimpleNamespace

from athena_whisper_topic.transcriber import build_transcript_result


def test_build_transcript_result_from_faster_whisper_shape() -> None:
    segments = [
        SimpleNamespace(start=0.0, end=1.2, text=" hello", words=None),
        SimpleNamespace(start=1.2, end=2.4, text="world ", words=None),
    ]
    info = SimpleNamespace(language="en", language_probability=0.99, duration=2.4)

    result = build_transcript_result(iter(segments), info)

    assert result.text == "hello world"
    assert result.language == "en"
    assert result.language_probability == 0.99
    assert result.duration == 2.4
    assert len(result.segments) == 2
