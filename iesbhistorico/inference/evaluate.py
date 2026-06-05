from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from iesbhistorico.config import DEFAULT_MODEL_PATH
from iesbhistorico.inference.batch_predict import load_inputs, predict_inputs, write_jsonl
from iesbhistorico.inference.model_loader import default_model_path
from iesbhistorico.inference.metrics import evaluate_labeled_predictions, prediction_distribution
from iesbhistorico.time_utils import decade_sort_key


DEFAULT_EVALUATION_INPUT = Path("evaluation_inputs/decade_labeled_phrases.jsonl")
DEFAULT_EVALUATION_DIR = Path("evaluation_results")


def run_evaluation(
    input_path: Path = DEFAULT_EVALUATION_INPUT,
    model_path: Path = DEFAULT_MODEL_PATH,
    output_dir: Path = DEFAULT_EVALUATION_DIR,
    run_id: str | None = None,
    model_type: str = "profile",
) -> dict[str, Any]:
    if model_path == DEFAULT_MODEL_PATH and model_type != "profile":
        model_path = default_model_path(model_type)
    run_id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    inputs = load_inputs(input_path)
    results = predict_inputs(inputs, model_path, model_type)
    metrics = evaluate_labeled_predictions(results)
    distribution = prediction_distribution(results)

    write_jsonl(results, run_dir / "predictions.jsonl")
    _write_metrics_json(metrics, distribution, run_dir / "metrics.json")
    _write_confusion_csv(metrics["confusion"], run_dir / "confusion_matrix.csv")
    _write_classification_report_markdown(metrics["classification"], run_dir / "classification_report.md")
    _write_classification_report_json(metrics["classification"], run_dir / "classification_report.json")
    _write_classification_report_csv(metrics["classification"], run_dir / "classification_report.csv")
    _write_metrics_markdown(metrics, distribution, run_dir / "metrics.md", input_path, model_path, run_id, model_type)
    _write_latest_pointer(output_dir, run_id)
    return {"run_id": run_id, "run_dir": str(run_dir), "metrics": metrics}


def _write_metrics_json(metrics: dict[str, Any], distribution: dict[str, int], path: Path) -> None:
    payload = {"metrics": metrics, "prediction_distribution": distribution}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_confusion_csv(confusion: dict[str, dict[str, int]], path: Path) -> None:
    decades = sorted(
        {decade for decade in confusion} | {decade for row in confusion.values() for decade in row},
        key=decade_sort_key,
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["expected\\predicted", *decades])
        for expected in decades:
            row = confusion.get(expected, {})
            writer.writerow([expected, *[row.get(predicted, 0) for predicted in decades]])


def _write_classification_report_json(classification: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(classification, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_classification_report_csv(classification: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["decade", "support", "precision", "recall", "f1_score", "correct", "errors", "confused_with"])
        for decade, row in classification["classes"].items():
            writer.writerow(
                [
                    decade,
                    row["support"],
                    f"{row['precision']:.6f}",
                    f"{row['recall']:.6f}",
                    f"{row['f1_score']:.6f}",
                    row["correct"],
                    row["errors"],
                    _format_confusions(row["confused_with"]),
                ]
            )


def _write_classification_report_markdown(classification: dict[str, Any], path: Path) -> None:
    lines = [
        "# Classification report",
        "",
        "## Summary",
        "",
        f"- Macro precision: {classification['macro_precision']:.4f}",
        f"- Macro recall: {classification['macro_recall']:.4f}",
        f"- Macro F1-score: {classification['macro_f1_score']:.4f}",
        f"- Weighted precision: {classification['weighted_precision']:.4f}",
        f"- Weighted recall: {classification['weighted_recall']:.4f}",
        f"- Weighted F1-score: {classification['weighted_f1_score']:.4f}",
        f"- Micro precision: {classification['micro_precision']:.4f}",
        f"- Micro recall: {classification['micro_recall']:.4f}",
        f"- Micro F1-score: {classification['micro_f1_score']:.4f}",
        "",
        "## By Decade",
        "",
        "| Decade | Support | Precision | Recall | F1-score | Correct | Errors | Main confusions |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for decade, row in classification["classes"].items():
        lines.append(
            "| {decade} | {support} | {precision:.4f} | {recall:.4f} | {f1:.4f} | {correct} | {errors} | {confusions} |".format(
                decade=decade,
                support=row["support"],
                precision=row["precision"],
                recall=row["recall"],
                f1=row["f1_score"],
                correct=row["correct"],
                errors=row["errors"],
                confusions=_format_confusions(row["confused_with"]),
            )
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_metrics_markdown(
    metrics: dict[str, Any],
    distribution: dict[str, int],
    path: Path,
    input_path: Path,
    model_path: Path,
    run_id: str,
    model_type: str,
) -> None:
    lines = [
        "# Evaluation metrics",
        "",
        f"Run ID: `{run_id}`",
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"Input file: `{input_path.as_posix()}`",
        f"Model file: `{model_path.as_posix()}`",
        f"Model type: `{model_type}`",
        "",
        "## Summary",
        "",
        f"- Total labeled inputs: {metrics['total']}",
        f"- Top-1 accuracy: {metrics['top1_accuracy']:.4f} ({metrics['top1_correct']}/{metrics['total']})",
        f"- Top-3 accuracy: {metrics['top3_accuracy']:.4f} ({metrics['top3_correct']}/{metrics['total']})",
        f"- Mean absolute decade error: {metrics['mean_absolute_decade_error']:.4f}",
        f"- Macro precision: {metrics['classification']['macro_precision']:.4f}",
        f"- Macro recall: {metrics['classification']['macro_recall']:.4f}",
        f"- Macro F1-score: {metrics['classification']['macro_f1_score']:.4f}",
        f"- Weighted precision: {metrics['classification']['weighted_precision']:.4f}",
        f"- Weighted recall: {metrics['classification']['weighted_recall']:.4f}",
        f"- Weighted F1-score: {metrics['classification']['weighted_f1_score']:.4f}",
        f"- Mean confidence for correct top-1 predictions: {metrics['confidence_correct_mean']:.6f}",
        f"- Mean confidence for wrong top-1 predictions: {metrics['confidence_wrong_mean']:.6f}",
        "",
        "## Prediction Distribution",
        "",
        "| Predicted decade | Count |",
        "| --- | ---: |",
    ]
    for decade, count in distribution.items():
        lines.append(f"| {decade} | {count} |")

    lines.extend(["", "## Metrics By Expected Decade", "", "| Expected decade | Total | Top-1 | Top-1 accuracy | Top-3 | Top-3 accuracy |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for decade, row in metrics["by_expected_decade"].items():
        lines.append(
            f"| {decade} | {row['total']} | {row['top1_correct']} | {row['top1_accuracy']:.4f} | {row['top3_correct']} | {row['top3_accuracy']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Classification Metrics By Decade",
            "",
            "| Decade | Support | Precision | Recall | F1-score | Correct | Errors | Main confusions |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for decade, row in metrics["classification"]["classes"].items():
        lines.append(
            "| {decade} | {support} | {precision:.4f} | {recall:.4f} | {f1:.4f} | {correct} | {errors} | {confusions} |".format(
                decade=decade,
                support=row["support"],
                precision=row["precision"],
                recall=row["recall"],
                f1=row["f1_score"],
                correct=row["correct"],
                errors=row["errors"],
                confusions=_format_confusions(row["confused_with"]),
            )
        )

    lines.extend(["", "## Metrics By Input Size", "", "| Input size | Total | Top-1 | Top-1 accuracy | Top-3 | Top-3 accuracy | Mean confidence |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for group, row in metrics["by_input_size"].items():
        lines.append(
            f"| {group} | {row['total']} | {row['top1_correct']} | {row['top1_accuracy']:.4f} | {row['top3_correct']} | {row['top3_accuracy']:.4f} | {row.get('confidence_mean', 0.0):.6f} |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def _write_latest_pointer(output_dir: Path, run_id: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "latest_run.txt").write_text(run_id, encoding="utf-8")


def _format_confusions(confusions: dict[str, int]) -> str:
    if not confusions:
        return ""
    return ", ".join(f"{decade}: {count}" for decade, count in confusions.items())


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate labeled phrase inputs and write versioned metrics.")
    parser.add_argument("--input", type=Path, default=DEFAULT_EVALUATION_INPUT)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--model-type", choices=["profile", "tfidf"], default="profile")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_EVALUATION_DIR)
    parser.add_argument("--run-id")
    args = parser.parse_args()

    result = run_evaluation(args.input, args.model, args.output_dir, args.run_id, args.model_type)
    print(json.dumps({"run_id": result["run_id"], "run_dir": result["run_dir"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
