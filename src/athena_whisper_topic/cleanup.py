from __future__ import annotations

import re


_PHRASE_REPLACEMENTS = (
    (re.compile(r"\bnew\s+paragraph\b", re.IGNORECASE), "\n\n"),
    (re.compile(r"\bnew\s+line\b", re.IGNORECASE), "\n"),
    (re.compile(r"\bcomma\b", re.IGNORECASE), ","),
    (re.compile(r"\bperiod\b", re.IGNORECASE), "."),
    (re.compile(r"\bfull\s+stop\b", re.IGNORECASE), "."),
    (re.compile(r"\bquestion\s+mark\b", re.IGNORECASE), "?"),
    (re.compile(r"\bexclamation\s+(point|mark)\b", re.IGNORECASE), "!"),
    (re.compile(r"\bcolon\b", re.IGNORECASE), ":"),
    (re.compile(r"\bsemicolon\b", re.IGNORECASE), ";"),
)


def cleanup_dictation_text(text: str, append_space: bool = False) -> str:
    """Normalize a short dictation transcript for insertion into a text field."""
    cleaned = text.strip()
    for pattern, replacement in _PHRASE_REPLACEMENTS:
        cleaned = pattern.sub(replacement, cleaned)

    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    cleaned = re.sub(r" +([,.;:?!])", r"\1", cleaned)
    cleaned = re.sub(r"([,;:])(?=\S)", r"\1 ", cleaned)
    cleaned = re.sub(r"([.?!])(?=[A-Za-z0-9])", r"\1 ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()

    if append_space and cleaned and not cleaned.endswith((" ", "\n")):
        cleaned += " "
    return cleaned
