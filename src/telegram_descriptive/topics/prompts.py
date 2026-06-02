"""Prompt builders for topic classification."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from telegram_descriptive.topics.taxonomy import TELEGRAM_TOPICS_V1


def taxonomy_prompt() -> str:
    bullets = "\n".join(f"- {topic.key}: {topic.description}" for topic in TELEGRAM_TOPICS_V1)
    return (
        "Classify the Telegram channel using only the evidence provided. "
        "Return JSON with keys topic_key, confidence, function_axis, and rationale.\n\n"
        f"Allowed topics:\n{bullets}"
    )


def evidence_bundle(channel: Mapping[str, object], messages: Iterable[Mapping[str, object]], max_messages: int = 12) -> str:
    lines = [
        f"title: {channel.get('channel_name', '')}",
        f"url: {channel.get('channel_url', '')}",
        f"about: {channel.get('about') or channel.get('description') or ''}",
        "messages:",
    ]
    for idx, message in enumerate(messages):
        if idx >= max_messages:
            break
        text = str(message.get("text_for_topics") or message.get("post_content") or "").strip()
        if len(text) > 500:
            text = text[:500] + "..."
        lines.append(f"- {text}")
    return "\n".join(lines)

