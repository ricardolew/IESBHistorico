from __future__ import annotations

import argparse
import logging
from pathlib import Path

import duckdb

from iesbhistorico.config import PARQUET_DIR, ensure_data_dirs
from iesbhistorico.logging_utils import configure_logging
from iesbhistorico.storage.partitioned_parquet import dataset_glob, replace_dataset

LOGGER = logging.getLogger(__name__)


def build_features(parquet_dir: Path = PARQUET_DIR, min_count: int = 2) -> int:
    ensure_data_dirs()
    timeline_glob = dataset_glob(parquet_dir, "phrase_timelines")
    stats_glob = dataset_glob(parquet_dir, "phrase_statistics")
    with duckdb.connect(":memory:") as connection:
        features = connection.execute(
            """
            WITH decade_scores AS (
                SELECT
                    phrase_hash,
                    phrase,
                    decade,
                    SUM(normalized_frequency) AS decade_score,
                    SUM(raw_count) AS decade_raw_count
                FROM read_parquet(?)
                GROUP BY phrase_hash, phrase, decade
            ),
            totals AS (
                SELECT phrase_hash, SUM(decade_score) AS total_score
                FROM decade_scores
                GROUP BY phrase_hash
            )
            SELECT
                s.phrase_hash,
                s.phrase,
                s.first_year,
                s.last_year,
                s.peak_year,
                s.peak_decade,
                s.total_count,
                s.temporal_entropy,
                d.decade,
                d.decade_score,
                d.decade_raw_count,
                CASE
                    WHEN t.total_score = 0 THEN 0.0
                    ELSE d.decade_score / t.total_score
                END AS target_probability
            FROM read_parquet(?) s
            JOIN decade_scores d USING (phrase_hash, phrase)
            JOIN totals t USING (phrase_hash)
            WHERE s.total_count >= ?
            ORDER BY s.phrase, d.decade
            """,
            [timeline_glob, stats_glob, min_count],
        ).fetchdf()

    replace_dataset(features, parquet_dir, "features")
    LOGGER.info("Built %s feature rows", len(features))
    return len(features)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build recomputable feature Parquet from timelines.")
    parser.add_argument("--parquet-dir", type=Path, default=PARQUET_DIR)
    parser.add_argument("--min-count", type=int, default=2)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)
    build_features(args.parquet_dir, args.min_count)


if __name__ == "__main__":
    main()
