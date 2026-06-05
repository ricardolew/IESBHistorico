from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

from iesbhistorico.config import DEFAULT_DATASET_PATH, PARQUET_DIR, ensure_data_dirs
from iesbhistorico.logging_utils import configure_logging
from iesbhistorico.storage.partitioned_parquet import read_dataset
from iesbhistorico.time_utils import decade_sort_key

LOGGER = logging.getLogger(__name__)


def build_dataset(
    parquet_dir: Path = PARQUET_DIR,
    output_path: Path = DEFAULT_DATASET_PATH,
) -> int:
    ensure_data_dirs()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    features = read_dataset(parquet_dir, "features")
    if features.empty:
        raise FileNotFoundError(f"No feature Parquet rows found under {parquet_dir / 'features'}")

    by_phrase: dict[str, list[dict]] = defaultdict(list)
    for record in features.to_dict(orient="records"):
        by_phrase[str(record["phrase_hash"])].append(record)

    written = 0
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        for phrase_hash in sorted(by_phrase, key=lambda key: by_phrase[key][0]["phrase"]):
            rows = sorted(by_phrase[phrase_hash], key=lambda row: decade_sort_key(str(row["decade"])))
            first = rows[0]
            target = {str(row["decade"]): float(row["target_probability"]) for row in rows}
            record = {
                "phrase": first["phrase"],
                "phrase_hash": phrase_hash,
                "features": {
                    "first_year": int(first["first_year"]),
                    "last_year": int(first["last_year"]),
                    "peak_year": int(first["peak_year"]),
                    "peak_decade": first["peak_decade"],
                    "total_count": int(first["total_count"]),
                    "temporal_entropy": float(first["temporal_entropy"]),
                },
                "target": target,
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
    tmp_path.replace(output_path)
    LOGGER.info("Wrote %s training rows to %s", written, output_path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Build JSONL training dataset from feature Parquet.")
    parser.add_argument("--parquet-dir", type=Path, default=PARQUET_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)
    build_dataset(args.parquet_dir, args.output)


if __name__ == "__main__":
    main()
