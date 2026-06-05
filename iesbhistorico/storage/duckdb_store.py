from __future__ import annotations

import argparse
import logging
from pathlib import Path

import duckdb

from iesbhistorico.config import PARQUET_DIR, ensure_data_dirs
from iesbhistorico.logging_utils import configure_logging
from iesbhistorico.storage.partitioned_parquet import dataset_glob

LOGGER = logging.getLogger(__name__)

DATASETS = ["articles", "phrases", "phrase_timelines", "phrase_statistics", "features", "embeddings"]


def validate_duckdb_parquet_views(parquet_dir: Path = PARQUET_DIR, datasets: list[str] | None = None) -> dict[str, int]:
    ensure_data_dirs()
    selected = datasets or DATASETS
    counts: dict[str, int] = {}
    with duckdb.connect(":memory:") as connection:
        for dataset in selected:
            files = list((parquet_dir / dataset).glob("**/*.parquet"))
            if not files:
                LOGGER.info("DuckDB validation skipped missing dataset: %s", dataset)
                continue
            glob = dataset_glob(parquet_dir, dataset)
            LOGGER.info("DuckDB querying Parquet dataset %s from %s", dataset, glob)
            count = connection.execute("SELECT COUNT(*) FROM read_parquet(?)", [glob]).fetchone()[0]
            counts[dataset] = int(count)
            LOGGER.info("DuckDB counted %s rows in %s", count, dataset)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate DuckDB analytical queries over Parquet datasets.")
    parser.add_argument("--parquet-dir", type=Path, default=PARQUET_DIR)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)
    validate_duckdb_parquet_views(args.parquet_dir)


if __name__ == "__main__":
    main()
