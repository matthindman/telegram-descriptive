"""Manual/LLM adjudication merge helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def apply_adjudications(
    predictions: Iterable[Mapping[str, Any]],
    adjudications: Iterable[Mapping[str, Any]],
    key: str = "entity_id",
) -> list[dict[str, Any]]:
    adjudication_by_key = {row[key]: row for row in adjudications if key in row}
    output: list[dict[str, Any]] = []
    for prediction in predictions:
        merged = dict(prediction)
        adjudication = adjudication_by_key.get(prediction.get(key))
        if adjudication:
            merged["language_label_original"] = merged.get("language_label")
            merged["language_label"] = adjudication.get("adjudicated_language", merged.get("language_label"))
            merged["language_adjudicated"] = True
            merged["language_adjudicator"] = adjudication.get("adjudicator")
        else:
            merged["language_adjudicated"] = False
        output.append(merged)
    return output

