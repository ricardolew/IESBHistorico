from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from iesbhistorico.normalization.article_cleaner import STOPWORDS, clean_phrase, normalize_text, tokenize


@dataclass(frozen=True)
class ExtractedPhrase:
    phrase: str
    context: str
    frequency: int = 1


def extract_phrases(
    text: str,
    min_n: int = 1,
    max_n: int = 4,
    max_phrases: int | None = 300,
    context_radius: int = 40,
) -> list[ExtractedPhrase]:
    normalized = normalize_text(text)
    tokens = tokenize(normalized)
    counts: Counter[str] = Counter()

    for size in range(min_n, max_n + 1):
        for index in range(0, len(tokens) - size + 1):
            window = tokens[index : index + size]
            if window[0] in STOPWORDS or window[-1] in STOPWORDS:
                continue
            phrase = clean_phrase(" ".join(window))
            if phrase:
                counts[phrase] += 1

    phrases = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    if max_phrases is not None:
        phrases = phrases[:max_phrases]
    return [
        ExtractedPhrase(phrase=phrase, context=_context_for_phrase(normalized, phrase, context_radius), frequency=count)
        for phrase, count in phrases
    ]


def _context_for_phrase(text: str, phrase: str, radius: int = 80) -> str:
    lower_text = text.lower()
    index = lower_text.find(phrase)
    if index < 0:
        return text[: radius * 2].strip()
    start = max(0, index - radius)
    end = min(len(text), index + len(phrase) + radius)
    return text[start:end].strip()
