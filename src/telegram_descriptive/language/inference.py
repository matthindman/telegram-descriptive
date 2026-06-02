"""Adapters for LID inference engines.

The repo does not vendor a model. Databricks notebooks can plug in OpenLID,
fastText, an LLM panel, or existing ``detected_language`` columns through this
interface.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from telegram_descriptive.language.segmentation import TextSegment


PredictionFn = Callable[[str], tuple[str, float]]


def predict_segments(segments: Iterable[TextSegment], predictor: PredictionFn) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for segment in segments:
        language, confidence = predictor(segment.text)
        rows.append(
            {
                "entity_id": segment.entity_id,
                "segment_id": segment.segment_id,
                "source_field": segment.source_field,
                "language": language,
                "confidence": float(confidence),
                "weight": segment.weight,
                "char_count": segment.char_count,
                "token_count": segment.token_count,
            }
        )
    return rows


def provisional_detected_language_predictor(label: str | None) -> tuple[str, float]:
    if label is None or str(label).strip() == "":
        return "NO TEXT", 0.0
    text = str(label).strip()
    confidence = 0.5 if text.upper() in {"NO TEXT", "UNKNOWN", "MIXED"} else 0.7
    return text, confidence

