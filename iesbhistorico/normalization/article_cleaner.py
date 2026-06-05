from __future__ import annotations

import re
import unicodedata


WHITESPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"([^\w\s])\1{1,}")
TOKEN_RE = re.compile(r"[a-z][a-z0-9'-]*")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "were",
    "with",
}


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    value = unicodedata.normalize("NFKC", text)
    value = value.replace("\u2019", "'")
    value = PUNCT_RE.sub(r"\1", value)
    value = WHITESPACE_RE.sub(" ", value)
    return value.strip()


def clean_phrase(phrase: str) -> str | None:
    value = normalize_text(phrase).lower()
    value = re.sub(r"[^a-z0-9'\-\s]", " ", value)
    value = WHITESPACE_RE.sub(" ", value).strip(" -'")
    if not value or len(value) < 3:
        return None
    if len(value) > 90:
        return None
    alpha_count = sum(char.isalpha() for char in value)
    if alpha_count / max(len(value), 1) < 0.55:
        return None
    if re.search(r"(.)\1{4,}", value):
        return None
    tokens = TOKEN_RE.findall(value)
    if not tokens:
        return None
    if all(token in STOPWORDS for token in tokens):
        return None
    return " ".join(tokens)


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(normalize_text(text).lower())
