from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from iesbhistorico.config import PARQUET_DIR, ensure_data_dirs
from iesbhistorico.logging_utils import configure_logging
from iesbhistorico.storage.partitioned_parquet import read_dataset, replace_dataset, stable_hash

LOGGER = logging.getLogger(__name__)


def build_embedding_manifest(parquet_dir: Path = PARQUET_DIR, model_name: str = "pending") -> int:
    """Build a deterministic embedding manifest without storing mutable cache state.

    Actual embedding vectors can be regenerated from this manifest later. The key
    point is that phrase identity and embedding identity are deterministic and
    stored as a recomputable Parquet dataset instead of a mutable cache.
    """

    ensure_data_dirs()
    stats = read_dataset(parquet_dir, "phrase_statistics", columns=["phrase_hash", "phrase"])
    if stats.empty:
        raise FileNotFoundError("Cannot build embedding manifest before phrase_statistics exists.")
    rows = []
    for row in stats.drop_duplicates("phrase_hash").itertuples(index=False):
        rows.append(
            {
                "phrase_hash": row.phrase_hash,
                "phrase": row.phrase,
                "model_name": model_name,
                "embedding_id": stable_hash({"phrase_hash": row.phrase_hash, "model_name": model_name}),
                "embedding_status": "not_generated",
            }
        )
    replace_dataset(pd.DataFrame(rows), parquet_dir, "embeddings")
    LOGGER.info("Built %s embedding manifest rows", len(rows))
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build deterministic embedding manifest Parquet.")
    parser.add_argument("--parquet-dir", type=Path, default=PARQUET_DIR)
    parser.add_argument("--model-name", default="pending")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)
    build_embedding_manifest(args.parquet_dir, args.model_name)


if __name__ == "__main__":
    main()
