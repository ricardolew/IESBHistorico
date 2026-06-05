from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb

from iesbhistorico.config import PARQUET_DIR, REPORTS_DIR, ensure_data_dirs
from iesbhistorico.storage.partitioned_parquet import dataset_glob
from iesbhistorico.time_utils import decade_sort_key


DEFAULT_MARKDOWN_OUTPUT = Path("docs/generated/corpus_distribution.md")
DEFAULT_JSON_OUTPUT = REPORTS_DIR / "corpus_distribution.json"


def analyze_corpus_distribution(parquet_dir: Path = PARQUET_DIR) -> dict[str, Any]:
    ensure_data_dirs()
    report: dict[str, Any] = {}
    with duckdb.connect(":memory:") as connection:
        if _has_dataset(parquet_dir, "articles"):
            report["articles_by_decade"] = _query_counts(connection, dataset_glob(parquet_dir, "articles"), "decade")
        if _has_dataset(parquet_dir, "phrases"):
            phrase_glob = dataset_glob(parquet_dir, "phrases")
            report["phrase_rows_by_decade"] = _query_counts(connection, phrase_glob, "decade")
            report["phrase_frequency_by_decade"] = _query_sum(connection, phrase_glob, "decade", "frequency")
            report["unique_phrases_by_decade"] = _query_unique_phrases(connection, phrase_glob)
        if _has_dataset(parquet_dir, "features"):
            report["feature_rows_by_decade"] = _query_counts(connection, dataset_glob(parquet_dir, "features"), "decade")
            report["target_probability_by_decade"] = _query_sum(
                connection,
                dataset_glob(parquet_dir, "features"),
                "decade",
                "target_probability",
            )
    return report


def write_distribution_report(report: dict[str, Any], markdown_output: Path = DEFAULT_MARKDOWN_OUTPUT, json_output: Path = DEFAULT_JSON_OUTPUT) -> None:
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# Corpus distribution", ""]
    if not report:
        lines.append("No corpus datasets were found.")
    for section, rows in report.items():
        lines.extend([f"## {section}", "", "| Decade | Value |", "| --- | ---: |"])
        for decade, value in sorted(rows.items(), key=lambda item: decade_sort_key(item[0])):
            if isinstance(value, float):
                lines.append(f"| {decade} | {value:.6f} |")
            else:
                lines.append(f"| {decade} | {value} |")
        lines.append("")
    markdown_output.write_text("\n".join(lines), encoding="utf-8")


def _has_dataset(parquet_dir: Path, dataset: str) -> bool:
    return bool(list((parquet_dir / dataset).glob("**/*.parquet")))


def _query_counts(connection: duckdb.DuckDBPyConnection, glob: str, column: str) -> dict[str, int]:
    rows = connection.execute(
        f"SELECT {column}, COUNT(*) AS count FROM read_parquet(?) GROUP BY {column} ORDER BY {column}",
        [glob],
    ).fetchall()
    return {str(decade): int(count) for decade, count in rows}


def _query_sum(connection: duckdb.DuckDBPyConnection, glob: str, column: str, value_column: str) -> dict[str, float]:
    rows = connection.execute(
        f"SELECT {column}, SUM({value_column}) AS total FROM read_parquet(?) GROUP BY {column} ORDER BY {column}",
        [glob],
    ).fetchall()
    return {str(decade): float(total or 0.0) for decade, total in rows}


def _query_unique_phrases(connection: duckdb.DuckDBPyConnection, glob: str) -> dict[str, int]:
    rows = connection.execute(
        """
        SELECT decade, COUNT(DISTINCT phrase_hash) AS count
        FROM read_parquet(?)
        GROUP BY decade
        ORDER BY decade
        """,
        [glob],
    ).fetchall()
    return {str(decade): int(count) for decade, count in rows}


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze temporal corpus distribution from Parquet datasets.")
    parser.add_argument("--parquet-dir", type=Path, default=PARQUET_DIR)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    args = parser.parse_args()

    report = analyze_corpus_distribution(args.parquet_dir)
    write_distribution_report(report, args.markdown_output, args.json_output)
    print(json.dumps({"sections": list(report), "markdown_output": str(args.markdown_output), "json_output": str(args.json_output)}, indent=2))


if __name__ == "__main__":
    main()

