from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InputSize:
    token_count: int
    char_count: int
    group: str
    over_90_chars: bool


def classify_input_size(phrase: str) -> InputSize:
    tokens = [token for token in phrase.split() if token]
    token_count = len(tokens)
    char_count = len(phrase)
    if token_count == 1:
        group = "1_token"
    elif token_count <= 4:
        group = "2_4_tokens"
    elif token_count <= 8:
        group = "5_8_tokens"
    elif token_count <= 15:
        group = "9_15_tokens"
    else:
        group = "16_plus_tokens"
    return InputSize(
        token_count=token_count,
        char_count=char_count,
        group=group,
        over_90_chars=char_count > 90,
    )

