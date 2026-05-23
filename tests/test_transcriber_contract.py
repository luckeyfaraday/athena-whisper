from types import SimpleNamespace

from athena_whisper_topic.config import DictationConfig
from athena_whisper_topic.transcriber import FasterWhisperTranscriber, build_transcript_result


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


class _RecordingModel:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] | None = None

    def transcribe(self, _audio_path: str, **kwargs: object):
        self.kwargs = kwargs
        return iter(()), SimpleNamespace(language="es", language_probability=0.98, duration=0.0)


def test_transcriber_forwards_multilingual_options_and_auto_language(tmp_path) -> None:
    model = _RecordingModel()
    config = DictationConfig(language="auto", multilingual=True, task="translate")
    transcriber = FasterWhisperTranscriber(config, _model=model)

    transcriber.transcribe_file(tmp_path / "speech.wav")

    assert model.kwargs is not None
    assert model.kwargs["language"] is None
    assert model.kwargs["multilingual"] is True
    assert model.kwargs["task"] == "translate"


def test_transcriber_forwards_fixed_language(tmp_path) -> None:
    model = _RecordingModel()
    transcriber = FasterWhisperTranscriber(DictationConfig(language="de"), _model=model)

    transcriber.transcribe_file(tmp_path / "speech.wav")

    assert model.kwargs is not None
    assert model.kwargs["language"] == "de"
