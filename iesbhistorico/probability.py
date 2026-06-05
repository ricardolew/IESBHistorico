from __future__ import annotations

import math


def normalize_distribution(scores: dict[str, float]) -> dict[str, float]:
    cleaned = {key: max(0.0, float(value)) for key, value in scores.items()}
    total = sum(cleaned.values())
    if total <= 0:
        if not cleaned:
            return {}
        value = 1.0 / len(cleaned)
        return {key: value for key in cleaned}
    return {key: value / total for key, value in cleaned.items()}


def softmax(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    max_score = max(scores.values())
    exp_scores = {key: math.exp(value - max_score) for key, value in scores.items()}
    return normalize_distribution(exp_scores)


def top_decade(distribution: dict[str, float]) -> tuple[str | None, float]:
    if not distribution:
        return None, 0.0
    decade, probability = max(distribution.items(), key=lambda item: item[1])
    return decade, probability
