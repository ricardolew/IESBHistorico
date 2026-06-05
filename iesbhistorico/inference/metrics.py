from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from iesbhistorico.time_utils import decade_sort_key


def evaluate_labeled_predictions(results: list[dict[str, Any]], top_k: int = 3) -> dict[str, Any]:
    labeled = [row for row in results if row.get("expected_decade")]
    total = len(labeled)
    top1 = 0
    topk = 0
    distance_sum = 0
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    by_decade: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "top1": 0, "topk": 0})
    by_size: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "top1": 0, "topk": 0, "confidence_sum": 0.0})
    confidence_correct: list[float] = []
    confidence_wrong: list[float] = []

    for row in labeled:
        expected = str(row["expected_decade"])
        predicted = str(row.get("top_decade"))
        ranked = [
            decade
            for decade, _probability in sorted(
                row.get("decades", {}).items(),
                key=lambda item: float(item[1]),
                reverse=True,
            )
        ]
        is_top1 = predicted == expected
        is_topk = expected in ranked[:top_k]
        confidence = float(row.get("confidence") or 0.0)
        size_group = str(row.get("input_size_group") or "unknown")

        top1 += int(is_top1)
        topk += int(is_topk)
        distance_sum += abs(decade_sort_key(predicted) - decade_sort_key(expected)) // 10
        confusion[expected][predicted] += 1

        by_decade[expected]["total"] += 1
        by_decade[expected]["top1"] += int(is_top1)
        by_decade[expected]["topk"] += int(is_topk)

        by_size[size_group]["total"] += 1
        by_size[size_group]["top1"] += int(is_top1)
        by_size[size_group]["topk"] += int(is_topk)
        by_size[size_group]["confidence_sum"] += confidence

        if is_top1:
            confidence_correct.append(confidence)
        else:
            confidence_wrong.append(confidence)

    return {
        "total": total,
        "top1_correct": top1,
        "top3_correct": topk,
        "top1_accuracy": top1 / total if total else 0.0,
        "top3_accuracy": topk / total if total else 0.0,
        "mean_absolute_decade_error": distance_sum / total if total else 0.0,
        "confidence_correct_mean": _mean(confidence_correct),
        "confidence_wrong_mean": _mean(confidence_wrong),
        "by_expected_decade": _rates(by_decade),
        "by_input_size": _rates(by_size),
        "confusion": {
            expected: dict(sorted(predicted.items(), key=lambda item: decade_sort_key(item[0])))
            for expected, predicted in sorted(confusion.items(), key=lambda item: decade_sort_key(item[0]))
        },
        "classification": _classification_metrics(labeled, confusion),
    }


def prediction_distribution(results: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get("top_decade")) for row in results).items(), key=lambda item: decade_sort_key(item[0])))


def _rates(groups: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for key, value in sorted(groups.items()):
        total = int(value["total"])
        output[key] = {
            "total": total,
            "top1_correct": int(value["top1"]),
            "top3_correct": int(value["topk"]),
            "top1_accuracy": value["top1"] / total if total else 0.0,
            "top3_accuracy": value["topk"] / total if total else 0.0,
        }
        if "confidence_sum" in value:
            output[key]["confidence_mean"] = value["confidence_sum"] / total if total else 0.0
    return output


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _classification_metrics(
    labeled: list[dict[str, Any]],
    confusion: dict[str, Counter[str]],
) -> dict[str, Any]:
    expected_counts = Counter(str(row["expected_decade"]) for row in labeled)
    predicted_counts = Counter(str(row.get("top_decade")) for row in labeled)
    classes = sorted(set(expected_counts) | set(predicted_counts), key=decade_sort_key)
    total = len(labeled)
    per_class: dict[str, dict[str, Any]] = {}
    true_positive_sum = 0
    weighted_precision_sum = 0.0
    weighted_recall_sum = 0.0
    weighted_f1_sum = 0.0

    for decade in classes:
        support = expected_counts.get(decade, 0)
        predicted_total = predicted_counts.get(decade, 0)
        true_positive = confusion.get(decade, Counter()).get(decade, 0)
        false_positive = predicted_total - true_positive
        false_negative = support - true_positive
        precision = _safe_divide(true_positive, true_positive + false_positive)
        recall = _safe_divide(true_positive, true_positive + false_negative)
        f1_score = _f1(precision, recall)
        errors = support - true_positive
        confused_with = {
            predicted: count
            for predicted, count in sorted(
                confusion.get(decade, Counter()).items(),
                key=lambda item: (-item[1], decade_sort_key(item[0])),
            )
            if predicted != decade and count > 0
        }
        per_class[decade] = {
            "support": support,
            "predicted": predicted_total,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "true_positives": true_positive,
            "false_positives": false_positive,
            "false_negatives": false_negative,
            "correct": true_positive,
            "errors": errors,
            "confused_with": confused_with,
        }
        true_positive_sum += true_positive
        weighted_precision_sum += precision * support
        weighted_recall_sum += recall * support
        weighted_f1_sum += f1_score * support

    macro_precision = _mean([row["precision"] for row in per_class.values()])
    macro_recall = _mean([row["recall"] for row in per_class.values()])
    macro_f1 = _mean([row["f1_score"] for row in per_class.values()])
    micro = _safe_divide(true_positive_sum, total)

    return {
        "classes": per_class,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1_score": macro_f1,
        "weighted_precision": _safe_divide(weighted_precision_sum, total),
        "weighted_recall": _safe_divide(weighted_recall_sum, total),
        "weighted_f1_score": _safe_divide(weighted_f1_sum, total),
        "micro_precision": micro,
        "micro_recall": micro,
        "micro_f1_score": micro,
    }


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0
