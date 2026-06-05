from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb

from iesbhistorico.config import PARQUET_DIR
from iesbhistorico.normalization.article_cleaner import clean_phrase
from iesbhistorico.storage.partitioned_parquet import dataset_glob, stable_hash
from iesbhistorico.time_utils import decade_sort_key


def inspect_phrase_target(phrase: str, parquet_dir: Path = PARQUET_DIR) -> dict[str, Any]:
    cleaned = clean_phrase(phrase) or phrase.lower().strip()
    phrase_hash = stable_hash({"phrase": cleaned})
    output: dict[str, Any] = {"phrase": phrase, "cleaned_phrase": cleaned, "phrase_hash": phrase_hash}
    with duckdb.connect(":memory:") as connection:
        if _has_dataset(parquet_dir, "phrase_timelines"):
            timeline = connection.execute(
                """
                SELECT year, decade, raw_count, normalized_frequency
                FROM read_parquet(?)
                WHERE phrase_hash = ?
                ORDER BY year
                """,
                [dataset_glob(parquet_dir, "phrase_timelines"), phrase_hash],
            ).fetchall()
            output["timeline"] = [
                {
                    "year": int(year),
                    "decade": str(decade),
                    "raw_count": int(raw_count),
                    "normalized_frequency": float(normalized_frequency),
                }
                for year, decade, raw_count, normalized_frequency in timeline
            ]
        if _has_dataset(parquet_dir, "features"):
            targets = connection.execute(
                """
                SELECT decade, target_probability, decade_raw_count, decade_score
                FROM read_parquet(?)
                WHERE phrase_hash = ?
                ORDER BY decade
                """,
                [dataset_glob(parquet_dir, "features"), phrase_hash],
            ).fetchall()
            output["target"] = {
                str(decade): {
                    "target_probability": float(probability),
                    "decade_raw_count": int(raw_count),
                    "decade_score": float(score),
                }
                for decade, probability, raw_count, score in targets
            }
            output["top_target_decades"] = [
                decade
                for decade, _payload in sorted(
                    output["target"].items(),
                    key=lambda item: item[1]["target_probability"],
                    reverse=True,
                )[:5]
            ]
    return output


def write_inspection_markdown(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phrase target inspection",
        "",
        f"Phrase: `{report['phrase']}`",
        f"Cleaned phrase: `{report['cleaned_phrase']}`",
        f"Phrase hash: `{report['phrase_hash']}`",
        "",
        "## Target by decade",
        "",
        "| Decade | Target probability | Raw count | Decade score |",
        "| --- | ---: | ---: | ---: |",
    ]
    for decade, payload in sorted(report.get("target", {}).items(), key=lambda item: decade_sort_key(item[0])):
        lines.append(
            f"| {decade} | {payload['target_probability']:.6f} | {payload['decade_raw_count']} | {payload['decade_score']:.10f} |"
        )
    lines.extend(["", "## Timeline", "", "| Year | Decade | Raw count | Normalized frequency |", "| ---: | --- | ---: | ---: |"])
    for row in report.get("timeline", []):
        lines.append(
            f"| {row['year']} | {row['decade']} | {row['raw_count']} | {row['normalized_frequency']:.10f} |"
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _has_dataset(parquet_dir: Path, dataset: str) -> bool:
    return bool(list((parquet_dir / dataset).glob("**/*.parquet")))


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect timeline and target distribution for one phrase.")
    parser.add_argument("phrase")
    parser.add_argument("--parquet-dir", type=Path, default=PARQUET_DIR)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = inspect_phrase_target(args.phrase, args.parquet_dir)
    if args.output:
        write_inspection_markdown(report, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

