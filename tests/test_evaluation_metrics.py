from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from iesbhistorico.inference.input_size import classify_input_size
from iesbhistorico.inference.input_validation import validate_input_file
from iesbhistorico.inference.metrics import evaluate_labeled_predictions


class EvaluationMetricsTest(unittest.TestCase):
    def test_input_size_groups(self) -> None:
        self.assertEqual(classify_input_size("telegraph").group, "1_token")
        self.assertEqual(classify_input_size("world trade center").group, "2_4_tokens")
        self.assertEqual(classify_input_size("the committee approved a new plan").group, "5_8_tokens")

    def test_labeled_prediction_metrics(self) -> None:
        rows = [
            {
                "expected_decade": "1900s",
                "top_decade": "1900s",
                "confidence": 0.8,
                "input_size_group": "2_4_tokens",
                "decades": {"1900s": 0.8, "1910s": 0.2},
            },
            {
                "expected_decade": "1910s",
                "top_decade": "1900s",
                "confidence": 0.7,
                "input_size_group": "2_4_tokens",
                "decades": {"1900s": 0.7, "1910s": 0.3},
            },
        ]
        metrics = evaluate_labeled_predictions(rows)
        self.assertEqual(metrics["total"], 2)
        self.assertEqual(metrics["top1_correct"], 1)
        self.assertEqual(metrics["top3_correct"], 2)
        self.assertAlmostEqual(metrics["top1_accuracy"], 0.5)
        self.assertIn("classification", metrics)

    def test_perfect_classification_metrics(self) -> None:
        rows = [
            _prediction("1900s", "1900s", {"1900s": 0.9, "1910s": 0.1}),
            _prediction("1910s", "1910s", {"1910s": 0.9, "1900s": 0.1}),
        ]
        metrics = evaluate_labeled_predictions(rows)
        classification = metrics["classification"]
        self.assertEqual(metrics["top1_correct"], 2)
        self.assertAlmostEqual(metrics["top1_accuracy"], 1.0)
        self.assertAlmostEqual(metrics["top3_accuracy"], 1.0)
        self.assertAlmostEqual(metrics["mean_absolute_decade_error"], 0.0)
        self.assertAlmostEqual(classification["macro_precision"], 1.0)
        self.assertAlmostEqual(classification["macro_recall"], 1.0)
        self.assertAlmostEqual(classification["macro_f1_score"], 1.0)
        self.assertAlmostEqual(classification["weighted_f1_score"], 1.0)

    def test_partially_incorrect_classification_metrics(self) -> None:
        rows = [
            _prediction("1900s", "1900s", {"1900s": 0.8, "1910s": 0.2}),
            _prediction("1900s", "1910s", {"1910s": 0.8, "1900s": 0.2}),
            _prediction("1910s", "1910s", {"1910s": 0.8, "1900s": 0.2}),
        ]
        metrics = evaluate_labeled_predictions(rows)
        classification = metrics["classification"]
        self.assertEqual(metrics["top1_correct"], 2)
        self.assertAlmostEqual(classification["classes"]["1900s"]["precision"], 1.0)
        self.assertAlmostEqual(classification["classes"]["1900s"]["recall"], 0.5)
        self.assertAlmostEqual(classification["classes"]["1900s"]["f1_score"], 2 / 3)
        self.assertAlmostEqual(classification["classes"]["1910s"]["precision"], 0.5)
        self.assertAlmostEqual(classification["classes"]["1910s"]["recall"], 1.0)
        self.assertAlmostEqual(classification["classes"]["1910s"]["f1_score"], 2 / 3)
        self.assertAlmostEqual(classification["macro_f1_score"], 2 / 3)
        self.assertAlmostEqual(classification["weighted_f1_score"], 2 / 3)

    def test_class_without_prediction_uses_zero_division_zero(self) -> None:
        rows = [
            _prediction("1900s", "1900s", {"1900s": 0.8, "1910s": 0.2}),
            _prediction("1910s", "1900s", {"1900s": 0.8, "1910s": 0.2}),
        ]
        classification = evaluate_labeled_predictions(rows)["classification"]
        self.assertAlmostEqual(classification["classes"]["1910s"]["precision"], 0.0)
        self.assertAlmostEqual(classification["classes"]["1910s"]["recall"], 0.0)
        self.assertAlmostEqual(classification["classes"]["1910s"]["f1_score"], 0.0)

    def test_predicted_class_without_real_example_is_reported(self) -> None:
        rows = [
            _prediction("1900s", "1910s", {"1910s": 0.8, "1900s": 0.2}),
        ]
        classification = evaluate_labeled_predictions(rows)["classification"]
        self.assertEqual(classification["classes"]["1910s"]["support"], 0)
        self.assertEqual(classification["classes"]["1910s"]["predicted"], 1)
        self.assertAlmostEqual(classification["classes"]["1910s"]["precision"], 0.0)
        self.assertAlmostEqual(classification["classes"]["1910s"]["recall"], 0.0)
        self.assertAlmostEqual(classification["classes"]["1910s"]["f1_score"], 0.0)

    def test_empty_evaluation_set_returns_zero_metrics(self) -> None:
        metrics = evaluate_labeled_predictions([])
        classification = metrics["classification"]
        self.assertEqual(metrics["total"], 0)
        self.assertAlmostEqual(metrics["top1_accuracy"], 0.0)
        self.assertAlmostEqual(metrics["top3_accuracy"], 0.0)
        self.assertEqual(classification["classes"], {})
        self.assertAlmostEqual(classification["macro_f1_score"], 0.0)
        self.assertAlmostEqual(classification["weighted_f1_score"], 0.0)

    def test_input_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "inputs.jsonl"
            path.write_text(
                json.dumps({"id": "A", "phrase": "test phrase", "expected_decade": "1900s"}) + "\n",
                encoding="utf-8",
            )
            report = validate_input_file(path, require_expected_decade=True)
            self.assertTrue(report["valid"])
            self.assertEqual(report["rows"], 1)


if __name__ == "__main__":
    unittest.main()


def _prediction(expected: str, predicted: str, decades: dict[str, float]) -> dict[str, object]:
    return {
        "expected_decade": expected,
        "top_decade": predicted,
        "confidence": decades[predicted],
        "input_size_group": "2_4_tokens",
        "decades": decades,
    }
