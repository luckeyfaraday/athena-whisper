from types import SimpleNamespace

from athena_whisper_topic.config import DictationConfig
from athena_whisper_topic.transcriber import (
    FasterWhisperTranscriber,
    GroqTranscriber,
    build_transcript_result,
    build_transcript_result_from_groq,
    create_transcriber,
)


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


def test_create_transcriber_selects_backend() -> None:
    assert isinstance(create_transcriber(DictationConfig()), FasterWhisperTranscriber)
    assert isinstance(create_transcriber(DictationConfig(backend="groq")), GroqTranscriber)


def test_build_transcript_result_from_groq_object_shape() -> None:
    response = SimpleNamespace(
        text="hello world",
        language="en",
        duration=2.4,
        segments=[
            SimpleNamespace(start=0.0, end=1.2, text=" hello"),
            SimpleNamespace(start=1.2, end=2.4, text="world "),
        ],
    )

    result = build_transcript_result_from_groq(response)

    assert result.text == "hello world"
    assert result.language == "en"
    assert result.language_probability is None
    assert result.duration == 2.4
    assert len(result.segments) == 2
    assert result.segments[0].text == "hello"


def test_build_transcript_result_from_groq_dict_shape() -> None:
    response = {
        "text": "hola mundo",
        "language": "es",
        "duration": 1.0,
        "segments": [{"start": 0.0, "end": 1.0, "text": "hola mundo"}],
    }

    result = build_transcript_result_from_groq(response)

    assert result.text == "hola mundo"
    assert result.language == "es"
    assert len(result.segments) == 1


class _RecordingGroqClient:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] | None = None
        self.endpoint: str | None = None
        self.audio = SimpleNamespace(
            transcriptions=SimpleNamespace(create=self._transcribe),
            translations=SimpleNamespace(create=self._translate),
        )

    def _transcribe(self, **kwargs: object):
        self.endpoint = "transcriptions"
        self.kwargs = kwargs
        return {"text": "ok", "language": "en", "duration": 0.0, "segments": []}

    def _translate(self, **kwargs: object):
        self.endpoint = "translations"
        self.kwargs = kwargs
        return {"text": "ok", "language": "en", "duration": 0.0, "segments": []}


def test_groq_transcriber_uses_transcriptions_with_fixed_language(tmp_path) -> None:
    client = _RecordingGroqClient()
    audio = tmp_path / "speech.wav"
    audio.write_bytes(b"RIFF....")
    transcriber = GroqTranscriber(DictationConfig(backend="groq", language="de"), _client=client)

    transcriber.transcribe_file(audio)

    assert client.endpoint == "transcriptions"
    assert client.kwargs is not None
    assert client.kwargs["language"] == "de"


def test_groq_transcriber_uses_translations_for_translate_task(tmp_path) -> None:
    client = _RecordingGroqClient()
    audio = tmp_path / "speech.wav"
    audio.write_bytes(b"RIFF....")
    transcriber = GroqTranscriber(
        DictationConfig(backend="groq", task="translate"), _client=client
    )

    transcriber.transcribe_file(audio)

    assert client.endpoint == "translations"
    assert client.kwargs is not None
    assert "language" not in client.kwargs
