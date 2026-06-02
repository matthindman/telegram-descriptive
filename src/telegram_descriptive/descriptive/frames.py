"""Build local channel/message analysis frames from normalized rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from telegram_descriptive.language.segmentation import best_text_for_message
from telegram_descriptive.tables import canonical_channel_id


def normalize_message_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        channel_id = canonical_channel_id(row.get("channel_id") or row.get("canonical_channel_id"))
        text = best_text_for_message(row)
        output.append(
            {
                **dict(row),
                "canonical_channel_id": channel_id,
                "text_for_lid": text,
                "text_for_topics": text,
                "has_text": bool(text.strip()),
                "is_forwarded": bool(row.get("shared_id") or row.get("repost_channel_data")),
                "is_reply": bool(row.get("replied_id") or row.get("is_reply")),
            }
        )
    return output


def join_channel_labels(
    channels: Iterable[Mapping[str, Any]],
    languages: Iterable[Mapping[str, Any]],
    topics: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    lang_by_id = {row.get("entity_id") or row.get("canonical_channel_id"): row for row in languages}
    topic_by_id = {row.get("entity_id") or row.get("canonical_channel_id"): row for row in topics}
    output: list[dict[str, Any]] = []
    for channel in channels:
        channel_id = canonical_channel_id(channel.get("canonical_channel_id") or channel.get("channel_id"))
        merged = dict(channel)
        merged["canonical_channel_id"] = channel_id
        lang = lang_by_id.get(channel_id, {})
        topic = topic_by_id.get(channel_id, {})
        merged["language_label"] = lang.get("language_label")
        merged["language_confidence"] = lang.get("language_confidence")
        merged["topic_label"] = topic.get("topic_label") or topic.get("topic_key")
        merged["topic_confidence"] = topic.get("topic_confidence") or topic.get("confidence")
        output.append(merged)
    return output

