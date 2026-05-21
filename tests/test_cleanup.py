from athena_whisper_topic.cleanup import cleanup_dictation_text


def test_cleanup_whitespace_and_spoken_punctuation() -> None:
    text = cleanup_dictation_text(" hello comma  world period ")
    assert text == "hello, world."


def test_cleanup_new_line_and_question_mark() -> None:
    text = cleanup_dictation_text("first line new line second line question mark")
    assert text == "first line\nsecond line?"


def test_cleanup_optional_append_space() -> None:
    assert cleanup_dictation_text("hello period", append_space=True) == "hello. "
