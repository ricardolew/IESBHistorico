from __future__ import annotations

import argparse
import json
from pathlib import Path

from iesbhistorico.config import DEFAULT_DATASET_PATH, DEFAULT_TFIDF_MODEL_PATH
from iesbhistorico.modeling.tfidf_model import train_tfidf_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Train an experimental TF-IDF decade classifier.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--model", type=Path, default=DEFAULT_TFIDF_MODEL_PATH)
    parser.add_argument("--max-rows", type=int, default=50000)
    args = parser.parse_args()

    rows = []
    with args.dataset.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
                if args.max_rows and len(rows) >= args.max_rows:
                    break
    model = train_tfidf_model(rows)
    model.save(args.model)
    print(json.dumps({"training_rows": len(rows), "model": str(args.model)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

