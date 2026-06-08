"""Topic classification adapters and rule-based fallback."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from telegram_descriptive.topics.taxonomy import taxonomy_dict


KEYWORD_RULES = {
    "crypto_finance": ("crypto", "bitcoin", "trading", "forex", "investment"),
    "health": ("health", "medical", "doctor", "covid", "vaccine"),
    "geopolitics_war": ("war", "military", "frontline", "missile", "army"),
    "news_politics": ("news", "politics", "election", "government", "parliament"),
    "commerce": ("shop", "sale", "discount", "marketplace", "order"),
    "file_sharing": ("download", "apk", "pdf", "leak", "torrent"),
    "education": ("course", "lesson", "exam", "school", "university"),
    "technology": ("software", "ai", "cyber", "developer", "programming"),
}


def rule_based_topic(text: str) -> dict[str, Any]:
    lower = text.lower()
    scores = {
        topic: sum(1 for keyword in keywords if keyword in lower)
        for topic, keywords in KEYWORD_RULES.items()
    }
    best_topic, best_score = max(scores.items(), key=lambda item: (item[1], item[0]))
    if best_score <= 0:
        return {"topic_key": "mixed_unknown", "confidence": 0.2, "method": "keyword_fallback"}
    return {
        "topic_key": best_topic,
        "confidence": min(0.85, 0.35 + 0.15 * best_score),
        "method": "keyword_fallback",
    }


def validate_topic_key(result: Mapping[str, Any]) -> dict[str, Any]:
    topics = taxonomy_dict()
    topic_key = str(result.get("topic_key") or "mixed_unknown")
    if topic_key not in topics:
        topic_key = "mixed_unknown"
    confidence = float(result.get("confidence") or 0.0)
    if not math.isfinite(confidence):
        confidence = 0.0
    return {
        **dict(result),
        "topic_key": topic_key,
        "topic_label": topics[topic_key].label,
        "confidence": max(0.0, min(1.0, confidence)),
    }
