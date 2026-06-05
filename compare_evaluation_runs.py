from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_run(output_dir: Path, run_id: str) -> dict[str, Any]:
    path = output_dir / run_id / "metrics.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {"run_id": run_id, **payload}


def write_comparison(runs: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Model comparison",
        "",
        "| Run | Top-1 accuracy | Top-3 accuracy | Mean decade error | Macro F1 | Weighted F1 | Correct confidence | Wrong confidence |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in runs:
        metrics = run["metrics"]
        classification = metrics.get("classification", {})
        lines.append(
            "| {run_id} | {top1:.4f} | {top3:.4f} | {error:.4f} | {macro_f1:.4f} | {weighted_f1:.4f} | {correct:.6f} | {wrong:.6f} |".format(
                run_id=run["run_id"],
                top1=metrics["top1_accuracy"],
                top3=metrics["top3_accuracy"],
                error=metrics["mean_absolute_decade_error"],
                macro_f1=classification.get("macro_f1_score", 0.0),
                weighted_f1=classification.get("weighted_f1_score", 0.0),
                correct=metrics["confidence_correct_mean"],
                wrong=metrics["confidence_wrong_mean"],
            )
        )
    lines.extend(["", "## Prediction distributions", ""])
    for run in runs:
        lines.extend([f"### {run['run_id']}", "", "| Decade | Count |", "| --- | ---: |"])
        for decade, count in run["prediction_distribution"].items():
            lines.append(f"| {decade} | {count} |")
        lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare versioned evaluation runs.")
    parser.add_argument("run_ids", nargs="+")
    parser.add_argument("--output-dir", type=Path, default=Path("evaluation_results"))
    parser.add_argument("--output", type=Path, default=Path("evaluation_results/model_comparison.md"))
    args = parser.parse_args()

    runs = [load_run(args.output_dir, run_id) for run_id in args.run_ids]
    write_comparison(runs, args.output)
    print(json.dumps({"runs": args.run_ids, "output": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
