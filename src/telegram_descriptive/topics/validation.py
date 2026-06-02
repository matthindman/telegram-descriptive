"""Topic validation queue helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def topic_review_queue(rows: Iterable[Mapping[str, Any]], limit: int | None = None) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for row in rows:
        confidence = float(row.get("topic_confidence") or row.get("confidence") or 0.0)
        follower_count = float(row.get("follower_count") or 0.0)
        priority = (1 - confidence) + min(1.0, follower_count / 1_000_000)
        scored.append({**dict(row), "review_priority_score": priority})
    scored.sort(key=lambda row: (-row["review_priority_score"], str(row.get("canonical_channel_id", ""))))
    return scored if limit is None else scored[:limit]

