from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from iesbhistorico.config import DEFAULT_DATASET_PATH, DEFAULT_MODEL_PATH, ensure_data_dirs
from iesbhistorico.logging_utils import configure_logging
from iesbhistorico.modeling.decade_model import DecadeProfileModel

LOGGER = logging.getLogger(__name__)


def train_model(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    model_path: Path = DEFAULT_MODEL_PATH,
    min_feature_weight: float = 0.0001,
    balance_decades: bool = False,
) -> DecadeProfileModel:
    ensure_data_dirs()
    if not dataset_path.exists():
        raise FileNotFoundError(f"Training dataset not found: {dataset_path}")

    rows: list[dict[str, Any]] = []
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    if not rows:
        raise ValueError(f"Training dataset has no rows: {dataset_path}")

    model = DecadeProfileModel()
    decade_weights = _decade_weights(rows) if balance_decades else None
    model.fit(rows, min_feature_weight=min_feature_weight, decade_weights=decade_weights)
    model.metadata = {
        "model_type": "profile",
        "balanced_decades": balance_decades,
        "min_feature_weight": min_feature_weight,
        "training_rows": len(rows),
        "decade_weights": decade_weights or {},
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = model_path.with_suffix(model_path.suffix + ".tmp")
    model.save(tmp_path)
    tmp_path.replace(model_path)
    LOGGER.info("Trained model with %s rows and saved %s", len(rows), model_path)
    return model


def _decade_weights(rows: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        weight = float(row.get("features", {}).get("total_count") or 1.0)
        for decade, probability in row.get("target", {}).items():
            totals[str(decade)] += float(probability) * weight
    if not totals:
        return {}
    mean = sum(totals.values()) / len(totals)
    return {decade: mean / total for decade, total in totals.items() if total > 0}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train phrase-to-decade probability model.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--min-feature-weight", type=float, default=0.0001)
    parser.add_argument("--balance-decades", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)
    train_model(args.dataset, args.model, args.min_feature_weight, args.balance_decades)


if __name__ == "__main__":
    main()
