from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from iesbhistorico.inference.input_size import classify_input_size
from iesbhistorico.time_utils import decade_sort_key


VALID_DECADES = {f"{year}s" for year in range(1850, 2030, 10)}


def validate_input_file(
    path: Path,
    require_expected_decade: bool = False,
    min_per_decade: int = 0,
) -> dict[str, Any]:
    rows = _load_jsonl(path)
    errors: list[str] = []
    ids: list[str] = []
    decade_counts: Counter[str] = Counter()
    size_counts: Counter[str] = Counter()

    for index, row in enumerate(rows, start=1):
        row_id = row.get("id")
        phrase = row.get("phrase")
        if not row_id:
            errors.append(f"line {index}: missing id")
        else:
            ids.append(str(row_id))
        if not phrase:
            errors.append(f"line {index}: missing phrase")
        else:
            size_counts[classify_input_size(str(phrase)).group] += 1

        expected = row.get("expected_decade")
        if require_expected_decade and not expected:
            errors.append(f"line {index}: missing expected_decade")
        if expected:
            if str(expected) not in VALID_DECADES:
                errors.append(f"line {index}: invalid expected_decade={expected}")
            else:
                decade_counts[str(expected)] += 1

    duplicate_ids = sorted(item for item, count in Counter(ids).items() if count > 1)
    for row_id in duplicate_ids:
        errors.append(f"duplicate id: {row_id}")

    if min_per_decade > 0:
        for decade in sorted(decade_counts or VALID_DECADES, key=decade_sort_key):
            count = decade_counts.get(decade, 0)
            if count < min_per_decade:
                errors.append(f"decade {decade} has {count} examples; expected at least {min_per_decade}")

    return {
        "path": str(path),
        "valid": not errors,
        "errors": errors,
        "rows": len(rows),
        "duplicate_ids": duplicate_ids,
        "decade_counts": dict(sorted(decade_counts.items(), key=lambda item: decade_sort_key(item[0]))),
        "size_counts": dict(sorted(size_counts.items())),
    }


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {error}") from error
    return rows

