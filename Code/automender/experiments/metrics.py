from __future__ import annotations

from typing import Dict


def repair_metrics(tp: int, fp: int, fn: int) -> Dict[str, float]:
    def divide(numerator: float, denominator: float) -> float:
        return numerator / denominator if denominator else 0.0
    precision = divide(tp, tp + fp)
    recall = divide(tp, tp + fn)
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "iou": divide(tp, tp + fp + fn),
        "precision": precision, "recall": recall,
        "f1": divide(2 * precision * recall, precision + recall),
    }
