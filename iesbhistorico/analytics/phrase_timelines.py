from __future__ import annotations

import argparse
import logging
from pathlib import Path

import duckdb

from iesbhistorico.config import PARQUET_DIR, ensure_data_dirs
from iesbhistorico.logging_utils import configure_logging
from iesbhistorico.storage.partitioned_parquet import dataset_glob, replace_dataset

LOGGER = logging.getLogger(__name__)


def rebuild_timelines(parquet_dir: Path = PARQUET_DIR) -> dict[str, int]:
    ensure_data_dirs()
    phrase_glob = dataset_glob(parquet_dir, "phrases")
    with duckdb.connect(":memory:") as connection:
        _ensure_dataset_exists(parquet_dir, "phrases")
        LOGGER.info("DuckDB reading phrase partitions from %s", phrase_glob)

        timelines = connection.execute(
            """
            WITH yearly AS (
                SELECT year, SUM(frequency) AS total_frequency
                FROM read_parquet(?)
                GROUP BY year
            )
            SELECT
                p.phrase_hash,
                p.phrase,
                p.year,
                p.decade,
                CAST(SUM(p.frequency) AS BIGINT) AS raw_count,
                CAST(SUM(p.frequency) AS DOUBLE) / y.total_frequency AS normalized_frequency
            FROM read_parquet(?) p
            JOIN yearly y USING (year)
            GROUP BY p.phrase_hash, p.phrase, p.year, p.decade, y.total_frequency
            ORDER BY p.phrase, p.year
            """,
            [phrase_glob, phrase_glob],
        ).fetchdf()

        stats = connection.execute(
            """
            WITH yearly_counts AS (
                SELECT phrase_hash, phrase, year, decade, SUM(frequency) AS raw_count
                FROM read_parquet(?)
                GROUP BY phrase_hash, phrase, year, decade
            ),
            phrase_totals AS (
                SELECT
                    phrase_hash,
                    phrase,
                    MIN(year) AS first_year,
                    MAX(year) AS last_year,
                    SUM(raw_count) AS total_count
                FROM yearly_counts
                GROUP BY phrase_hash, phrase
            ),
            ranked_years AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY phrase_hash
                        ORDER BY raw_count DESC, year ASC
                    ) AS rank
                FROM yearly_counts
            ),
            decade_counts AS (
                SELECT phrase_hash, decade, SUM(raw_count) AS decade_count
                FROM yearly_counts
                GROUP BY phrase_hash, decade
            ),
            ranked_decades AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY phrase_hash
                        ORDER BY decade_count DESC, decade ASC
                    ) AS rank
                FROM decade_counts
            ),
            entropy AS (
                SELECT
                    d.phrase_hash,
                    CASE
                        WHEN COUNT(*) <= 1 THEN 0.0
                        ELSE -SUM((d.decade_count / t.total_count) * LN(d.decade_count / t.total_count)) / LN(COUNT(*))
                    END AS temporal_entropy
                FROM decade_counts d
                JOIN phrase_totals t USING (phrase_hash)
                GROUP BY d.phrase_hash, t.total_count
            )
            SELECT
                t.phrase_hash AS phrase_hash,
                t.phrase,
                t.first_year,
                t.last_year,
                y.year AS peak_year,
                d.decade AS peak_decade,
                CAST(t.total_count AS BIGINT) AS total_count,
                e.temporal_entropy
            FROM phrase_totals t
            JOIN ranked_years y ON t.phrase_hash = y.phrase_hash AND y.rank = 1
            JOIN ranked_decades d ON t.phrase_hash = d.phrase_hash AND d.rank = 1
            JOIN entropy e ON t.phrase_hash = e.phrase_hash
            ORDER BY t.phrase
            """,
            [phrase_glob],
        ).fetchdf()

    replace_dataset(timelines, parquet_dir, "phrase_timelines")
    replace_dataset(stats, parquet_dir, "phrase_statistics")
    LOGGER.info("Rebuilt %s timeline rows and %s phrase statistics rows", len(timelines), len(stats))
    return {"phrase_timelines": len(timelines), "phrase_statistics": len(stats)}


def _ensure_dataset_exists(parquet_dir: Path, dataset: str) -> None:
    if not list((parquet_dir / dataset).glob("**/*.parquet")):
        raise FileNotFoundError(f"No Parquet files found for dataset: {parquet_dir / dataset}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild phrase timelines and statistics from phrase Parquet.")
    parser.add_argument("--parquet-dir", type=Path, default=PARQUET_DIR)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)
    rebuild_timelines(args.parquet_dir)


if __name__ == "__main__":
    main()
