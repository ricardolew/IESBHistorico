from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from iesbhistorico.config import PARQUET_DIR
from iesbhistorico.storage.partitioned_parquet import read_dataset, replace_dataset, stable_hash


def build_real_embeddings(
    parquet_dir: Path = PARQUET_DIR,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    max_rows: int = 1000,
) -> int:
    from sentence_transformers import SentenceTransformer

    stats = read_dataset(parquet_dir, "phrase_statistics", columns=["phrase_hash", "phrase"])
    if stats.empty:
        raise FileNotFoundError("Cannot build embeddings before phrase_statistics exists.")
    rows = stats.drop_duplicates("phrase_hash").head(max_rows)
    model = SentenceTransformer(model_name)
    vectors = model.encode(rows["phrase"].tolist(), show_progress_bar=True)
    output = pd.DataFrame(
        {
            "phrase_hash": rows["phrase_hash"].tolist(),
            "phrase": rows["phrase"].tolist(),
            "model_name": model_name,
            "embedding_id": [
                stable_hash({"phrase_hash": phrase_hash, "model_name": model_name})
                for phrase_hash in rows["phrase_hash"].tolist()
            ],
            "embedding_status": "generated",
            "embedding": [vector.tolist() for vector in vectors],
        }
    )
    replace_dataset(output, parquet_dir, "real_embeddings")
    return len(output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build optional real sentence embeddings for a controlled subset.")
    parser.add_argument("--parquet-dir", type=Path, default=PARQUET_DIR)
    parser.add_argument("--model-name", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--max-rows", type=int, default=1000)
    args = parser.parse_args()

    count = build_real_embeddings(args.parquet_dir, args.model_name, args.max_rows)
    print(json.dumps({"embeddings": count, "dataset": str(args.parquet_dir / "real_embeddings")}, indent=2))


if __name__ == "__main__":
    main()

