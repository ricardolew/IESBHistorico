from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from iesbhistorico.config import DEFAULT_MODEL_PATH
from iesbhistorico.inference.input_size import classify_input_size
from iesbhistorico.inference.model_loader import default_model_path, load_model
from iesbhistorico.probability import top_decade


DEFAULT_INPUT_PATH = Path("sample_inputs/phrases.jsonl")
DEFAULT_MARKDOWN_OUTPUT = Path("sample_inputs/results/predictions.md")
DEFAULT_JSONL_OUTPUT = Path("sample_inputs/results/predictions.jsonl")


def load_inputs(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not row.get("id") or not row.get("phrase"):
                raise ValueError(f"Invalid input row at {path}:{line_number}")
            rows.append(row)
    return rows


def predict_inputs(
    input_rows: list[dict[str, Any]],
    model_path: Path = DEFAULT_MODEL_PATH,
    model_type: str = "profile",
) -> list[dict[str, Any]]:
    model = load_model(model_type, model_path)
    results: list[dict[str, Any]] = []
    for row in input_rows:
        distribution = model.predict(str(row["phrase"]))
        decade, confidence = top_decade(distribution)
        expected_decade = row.get("expected_decade")
        input_size = classify_input_size(str(row["phrase"]))
        results.append(
            {
                **row,
                "input_size_group": input_size.group,
                "token_count": input_size.token_count,
                "char_count": input_size.char_count,
                "over_90_chars": input_size.over_90_chars,
                "top_decade": decade,
                "confidence": round(confidence, 6),
                "matches_expected": decade == expected_decade if expected_decade else None,
                "decades": {key: round(value, 6) for key, value in distribution.items()},
            }
        )
    return results


def write_jsonl(results: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
    tmp_path.replace(output_path)


def write_markdown(results: list[dict[str, Any]], output_path: Path, model_path: Path, input_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    directed = [row for row in results if row.get("group") == "directed"]
    random_rows = [row for row in results if row.get("group") == "random"]
    matches = [row for row in directed if row.get("matches_expected") is True]
    size_counts: dict[str, int] = {}
    for row in results:
        group = str(row.get("input_size_group") or "unknown")
        size_counts[group] = size_counts.get(group, 0) + 1

    lines = [
        "# Sample prediction results",
        "",
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"Input file: `{input_path.as_posix()}`",
        f"Model file: `{model_path.as_posix()}`",
        f"Total inputs: {len(results)}",
        f"Directed inputs: {len(directed)}",
        f"Random inputs: {len(random_rows)}",
        f"Directed matches: {len(matches)}/{len(directed)}",
        "",
        "## Input Sizes",
        "",
        "| Size group | Inputs |",
        "| --- | ---: |",
    ]
    for group, count in sorted(size_counts.items()):
        lines.append(f"| {group} | {count} |")

    lines.extend([
        "",
        "## Directed inputs",
        "",
        "| ID | Phrase | Size | Expected decade | Predicted decade | Confidence | Match |",
        "| --- | --- | --- | --- | --- | ---: | --- |",
    ])
    for row in directed:
        lines.append(
            "| {id} | {phrase} | {size} | {expected} | {predicted} | {confidence:.6f} | {match} |".format(
                id=row["id"],
                phrase=_escape_table(str(row["phrase"])),
                size=row.get("input_size_group") or "",
                expected=row.get("expected_decade") or "",
                predicted=row.get("top_decade") or "",
                confidence=float(row["confidence"]),
                match=_format_match(row.get("matches_expected")),
            )
        )

    lines.extend(
        [
            "",
            "## Random inputs",
            "",
            "| ID | Phrase | Size | Predicted decade | Confidence |",
            "| --- | --- | --- | --- | ---: |",
        ]
    )
    for row in random_rows:
        lines.append(
            "| {id} | {phrase} | {size} | {predicted} | {confidence:.6f} |".format(
                id=row["id"],
                phrase=_escape_table(str(row["phrase"])),
                size=row.get("input_size_group") or "",
                predicted=row.get("top_decade") or "",
                confidence=float(row["confidence"]),
            )
        )

    lines.extend(["", "## Full probability distributions", ""])
    for row in results:
        lines.extend(
            [
                f"### {row['id']} - {row['phrase']}",
                "",
                "```json",
                json.dumps(row["decades"], ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )

    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text("\n".join(lines), encoding="utf-8")
    tmp_path.replace(output_path)


def run_batch(
    input_path: Path = DEFAULT_INPUT_PATH,
    model_path: Path = DEFAULT_MODEL_PATH,
    markdown_output: Path = DEFAULT_MARKDOWN_OUTPUT,
    jsonl_output: Path = DEFAULT_JSONL_OUTPUT,
    model_type: str = "profile",
) -> list[dict[str, Any]]:
    inputs = load_inputs(input_path)
    results = predict_inputs(inputs, model_path, model_type)
    write_markdown(results, markdown_output, model_path, input_path)
    write_jsonl(results, jsonl_output)
    return results


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|")


def _format_match(value: object) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run batch predictions for the sample input repository.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--model-type", choices=["profile", "tfidf"], default="profile")
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--jsonl-output", type=Path, default=DEFAULT_JSONL_OUTPUT)
    args = parser.parse_args()

    model_path = default_model_path(args.model_type) if args.model == DEFAULT_MODEL_PATH else args.model
    results = run_batch(args.input, model_path, args.markdown_output, args.jsonl_output, args.model_type)
    print(
        json.dumps(
            {
                "inputs": len(results),
                "markdown_output": str(args.markdown_output),
                "jsonl_output": str(args.jsonl_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
