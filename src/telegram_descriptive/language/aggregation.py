"""Aggregate segment-level language predictions to channel/message labels."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from telegram_descriptive.tables import canonical_channel_id


def aggregate_language_predictions(
    predictions: Iterable[Mapping[str, Any]],
    entity_col: str = "entity_id",
    label_col: str = "language",
    confidence_col: str = "confidence",
    weight_col: str = "weight",
    mixed_margin: float = 0.15,
    min_total_weight: float = 0.1,
    no_text_label: str = "NO TEXT",
) -> list[dict[str, Any]]:
    """Weighted language aggregation with an explicit mixed/low-text branch."""

    scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    segment_counts: dict[str, int] = defaultdict(int)
    for row in predictions:
        entity = canonical_channel_id(row.get(entity_col))
        label = row.get(label_col)
        if not entity or not label:
            continue
        confidence = float(row.get(confidence_col, 1.0) or 0.0)
        weight = float(row.get(weight_col, 1.0) or 0.0)
        scores[entity][str(label)] += max(0.0, confidence * weight)
        segment_counts[entity] += 1

    output: list[dict[str, Any]] = []
    for entity, by_label in scores.items():
        total = sum(by_label.values())
        if total < min_total_weight:
            output.append(
                {
                    entity_col: entity,
                    "language_label": no_text_label,
                    "language_confidence": 0.0,
                    "language_margin": 0.0,
                    "language_evidence_weight": total,
                    "language_segment_count": segment_counts[entity],
                }
            )
            continue
        ranked = sorted(by_label.items(), key=lambda item: (-item[1], item[0]))
        top_label, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = (top_score - second_score) / total
        label = "MIXED" if len(ranked) > 1 and margin < mixed_margin else top_label
        output.append(
            {
                entity_col: entity,
                "language_label": label,
                "language_confidence": top_score / total,
                "language_margin": margin,
                "language_evidence_weight": total,
                "language_segment_count": segment_counts[entity],
            }
        )
    return output
