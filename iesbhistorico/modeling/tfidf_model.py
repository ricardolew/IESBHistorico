from __future__ import annotations

from pathlib import Path
from typing import Any

from iesbhistorico.probability import normalize_distribution
from iesbhistorico.time_utils import decade_sort_key


class TfidfDecadeModel:
    def __init__(self, pipeline: Any, decades: list[str]) -> None:
        self.pipeline = pipeline
        self.decades = sorted(decades, key=decade_sort_key)

    def predict(self, phrase: str) -> dict[str, float]:
        probabilities = self.pipeline.predict_proba([phrase])[0]
        classes = [str(item) for item in self.pipeline.classes_]
        scores = {decade: 0.0 for decade in self.decades}
        for class_name, probability in zip(classes, probabilities):
            scores[class_name] = float(probability)
        return normalize_distribution(dict(sorted(scores.items(), key=lambda item: decade_sort_key(item[0]))))

    def save(self, path: Path) -> None:
        from joblib import dump

        path.parent.mkdir(parents=True, exist_ok=True)
        dump({"pipeline": self.pipeline, "decades": self.decades, "metadata": {"model_type": "tfidf"}}, path)

    @classmethod
    def load(cls, path: Path) -> "TfidfDecadeModel":
        from joblib import load

        payload = load(path)
        return cls(payload["pipeline"], list(payload["decades"]))


def train_tfidf_model(rows: list[dict[str, Any]], max_rows: int | None = None) -> TfidfDecadeModel:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    selected = rows[:max_rows] if max_rows else rows
    phrases: list[str] = []
    labels: list[str] = []
    decades = sorted({decade for row in selected for decade in row.get("target", {})}, key=decade_sort_key)
    for row in selected:
        target = {str(decade): float(probability) for decade, probability in row.get("target", {}).items()}
        if not target:
            continue
        phrases.append(str(row["phrase"]))
        labels.append(max(target.items(), key=lambda item: item[1])[0])
    if len(set(labels)) < 2:
        raise ValueError("TF-IDF model requires at least two target decades.")

    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=1,
                    max_features=50000,
                ),
            ),
            ("classifier", LogisticRegression(max_iter=1000)),
        ]
    )
    pipeline.fit(phrases, labels)
    return TfidfDecadeModel(pipeline, decades)
