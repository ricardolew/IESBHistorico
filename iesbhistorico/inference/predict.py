from __future__ import annotations

import argparse
import json
from pathlib import Path

from iesbhistorico.config import DEFAULT_MODEL_PATH
from iesbhistorico.inference.model_loader import default_model_path, load_model
from iesbhistorico.probability import top_decade


def predict_phrase(phrase: str, model_path: Path = DEFAULT_MODEL_PATH, model_type: str = "profile") -> dict:
    model = load_model(model_type, model_path)
    distribution = model.predict(phrase)
    decade, confidence = top_decade(distribution)
    return {
        "phrase": phrase,
        "decades": {key: round(value, 6) for key, value in distribution.items()},
        "top_decade": decade,
        "confidence": round(confidence, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict decade probabilities for a phrase.")
    parser.add_argument("phrase")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--model-type", choices=["profile", "tfidf"], default="profile")
    args = parser.parse_args()

    model_path = default_model_path(args.model_type) if args.model == DEFAULT_MODEL_PATH else args.model
    print(json.dumps(predict_phrase(args.phrase, model_path, args.model_type), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
