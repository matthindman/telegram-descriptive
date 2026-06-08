"""Telegram text segmentation for language detection and topic evidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from telegram_descriptive.tables import canonical_channel_id


TEXT_FIELD_WEIGHTS = {
    "channel_name": 0.8,
    "about": 0.8,
    "description": 0.8,
    "post_title": 0.5,
    "post_content": 1.0,
    "all_text": 1.0,
    "searchable_text": 0.7,
    "image_text": 0.6,
    "transcript_text": 0.7,
}


@dataclass(frozen=True)
class TextSegment:
    entity_id: str
    segment_id: str
    source_field: str
    text: str
    weight: float
    char_count: int
    token_count: int


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\x00", " ").strip()
    return " ".join(text.split())


def segment_record(
    row: Mapping[str, Any],
    entity_id_col: str,
    fields: Mapping[str, float] | None = None,
    min_chars: int = 8,
) -> list[TextSegment]:
    """Create source-aware LID segments from a channel or message row."""

    entity_id = canonical_channel_id(row.get(entity_id_col))
    if entity_id is None:
        raise ValueError(f"missing entity id column {entity_id_col!r}")
    weights = fields or TEXT_FIELD_WEIGHTS
    segments: list[TextSegment] = []
    for field, weight in weights.items():
        text = normalize_text(row.get(field))
        if len(text) < min_chars:
            continue
        segments.append(
            TextSegment(
                entity_id=entity_id,
                segment_id=f"{entity_id}:{field}",
                source_field=field,
                text=text,
                weight=float(weight),
                char_count=len(text),
                token_count=len(text.split()),
            )
        )
    return segments


def best_text_for_message(row: Mapping[str, Any]) -> str:
    """Build a compact text field while retaining OCR/transcript signal."""

    ordered_fields = ("post_content", "all_text", "searchable_text", "image_text", "transcript_text")
    pieces = [normalize_text(row.get(field)) for field in ordered_fields]
    seen: set[str] = set()
    deduped: list[str] = []
    for piece in pieces:
        if piece and piece not in seen:
            deduped.append(piece)
            seen.add(piece)
    return "\n".join(deduped)
