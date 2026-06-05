from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from iesbhistorico.normalization.article_cleaner import clean_phrase, tokenize
from iesbhistorico.probability import normalize_distribution
from iesbhistorico.time_utils import decade_sort_key


DEFAULT_DECADES = [f"{year}s" for year in range(1850, 2030, 10)]


class DecadeProfileModel:
    """Small probabilistic text model for phrase -> decade distributions.

    It stores learned decade profiles for words and character n-grams. Prediction
    averages all matching feature profiles with a corpus prior, then normalizes.
    """

    def __init__(self) -> None:
        self.decades: list[str] = []
        self.prior: dict[str, float] = {}
        self.feature_profiles: dict[str, dict[str, float]] = {}
        self.feature_weights: dict[str, float] = {}
        self.metadata: dict[str, Any] = {"model_type": "profile"}

    def fit(
        self,
        rows: list[dict[str, Any]],
        min_feature_weight: float = 0.0001,
        decade_weights: dict[str, float] | None = None,
    ) -> None:
        decade_scores: dict[str, float] = defaultdict(float)
        feature_scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        feature_totals: dict[str, float] = defaultdict(float)
        decade_weights = decade_weights or {}

        for row in rows:
            phrase = str(row["phrase"])
            target = {str(key): float(value) for key, value in row["target"].items()}
            weight = math.log1p(float(row.get("features", {}).get("total_count") or 1.0))
            for decade, probability in target.items():
                adjusted_probability = probability * decade_weights.get(decade, 1.0)
                decade_scores[decade] += adjusted_probability * weight
            for feature in phrase_features(phrase):
                feature_totals[feature] += weight
                for decade, probability in target.items():
                    adjusted_probability = probability * decade_weights.get(decade, 1.0)
                    feature_scores[feature][decade] += adjusted_probability * weight

        self.decades = sorted(decade_scores, key=decade_sort_key)
        self.prior = normalize_distribution({decade: decade_scores[decade] for decade in self.decades})
        self.feature_profiles = {}
        self.feature_weights = {}

        for feature, scores in feature_scores.items():
            total = feature_totals[feature]
            if total < min_feature_weight:
                continue
            profile = normalize_distribution({decade: scores.get(decade, 0.0) for decade in self.decades})
            self.feature_profiles[feature] = profile
            self.feature_weights[feature] = total

    def predict(self, phrase: str) -> dict[str, float]:
        if not self.decades:
            self.decades = DEFAULT_DECADES
        if not self.prior:
            self.prior = normalize_distribution({decade: 1.0 for decade in self.decades})

        scores = {decade: self.prior.get(decade, 0.0) * 0.35 for decade in self.decades}
        total_weight = 0.35
        for feature in phrase_features(phrase):
            profile = self.feature_profiles.get(feature)
            if not profile:
                continue
            weight = min(4.0, math.log1p(self.feature_weights.get(feature, 1.0)))
            total_weight += weight
            for decade in self.decades:
                scores[decade] += profile.get(decade, 0.0) * weight

        if total_weight > 0:
            scores = {decade: value / total_weight for decade, value in scores.items()}
        return normalize_distribution(dict(sorted(scores.items(), key=lambda item: decade_sort_key(item[0]))))

    def save(self, path: Path) -> None:
        payload = {
            "decades": self.decades,
            "prior": self.prior,
            "feature_profiles": self.feature_profiles,
            "feature_weights": self.feature_weights,
            "metadata": self.metadata,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "DecadeProfileModel":
        model = cls()
        payload = json.loads(path.read_text(encoding="utf-8"))
        model.decades = list(payload.get("decades") or [])
        model.prior = {str(key): float(value) for key, value in payload.get("prior", {}).items()}
        model.feature_profiles = {
            str(feature): {str(decade): float(value) for decade, value in profile.items()}
            for feature, profile in payload.get("feature_profiles", {}).items()
        }
        model.feature_weights = {
            str(feature): float(value) for feature, value in payload.get("feature_weights", {}).items()
        }
        model.metadata = dict(payload.get("metadata") or {"model_type": "profile"})
        return model

    @classmethod
    def fallback(cls) -> "DecadeProfileModel":
        model = cls()
        model.decades = DEFAULT_DECADES
        model.prior = normalize_distribution({decade: 1.0 for decade in DEFAULT_DECADES})
        return model


def phrase_features(phrase: str) -> list[str]:
    cleaned = clean_phrase(phrase) or phrase.lower().strip()
    tokens = tokenize(cleaned)
    features: list[str] = []
    features.extend(f"w:{token}" for token in tokens)
    features.extend(f"b:{tokens[index]} {tokens[index + 1]}" for index in range(len(tokens) - 1))
    compact = f" {cleaned} "
    for size in (3, 4, 5):
        for index in range(0, max(0, len(compact) - size + 1)):
            gram = compact[index : index + size]
            if gram.strip():
                features.append(f"c{size}:{gram}")
    return sorted(set(features))
