"""Language validation sampling and summaries."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any


def confusion_counts(
    rows: Iterable[Mapping[str, Any]],
    truth_col: str = "adjudicated_language",
    pred_col: str = "language_label",
) -> dict[tuple[str, str], int]:
    counts: Counter[tuple[str, str]] = Counter()
    for row in rows:
        truth = row.get(truth_col)
        pred = row.get(pred_col)
        if truth is None or pred is None:
            continue
        counts[(str(truth), str(pred))] += 1
    return dict(counts)


def precision_recall_by_label(
    rows: Iterable[Mapping[str, Any]],
    truth_col: str = "adjudicated_language",
    pred_col: str = "language_label",
) -> list[dict[str, Any]]:
    pairs = confusion_counts(rows, truth_col=truth_col, pred_col=pred_col)
    labels = sorted({label for pair in pairs for label in pair})
    output: list[dict[str, Any]] = []
    for label in labels:
        tp = pairs.get((label, label), 0)
        fp = sum(count for (truth, pred), count in pairs.items() if pred == label and truth != label)
        fn = sum(count for (truth, pred), count in pairs.items() if truth == label and pred != label)
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        output.append({"label": label, "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall})
    return output


def review_priority(row: Mapping[str, Any]) -> str:
    confidence = float(row.get("language_confidence") or 0.0)
    follower_count = float(row.get("follower_count") or 0.0)
    label = str(row.get("language_label") or "")
    if follower_count >= 100_000 and confidence < 0.9:
        return "high_reach_low_confidence"
    if label in {"MIXED", "NO TEXT", "UNKNOWN"}:
        return "ambiguous_or_low_text"
    if confidence < 0.7:
        return "low_confidence"
    return "routine"

