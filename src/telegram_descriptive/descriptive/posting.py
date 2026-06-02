"""Posting frequency and recency helpers."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any


def parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def channel_posting_summary(rows: Iterable[Mapping[str, Any]], now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    by_channel: dict[str, list[datetime]] = defaultdict(list)
    for row in rows:
        channel = row.get("canonical_channel_id") or row.get("channel_id")
        published = parse_datetime(row.get("published_at") or row.get("created_at"))
        if channel and published:
            by_channel[str(channel)].append(published)
    output: list[dict[str, Any]] = []
    for channel, dates in by_channel.items():
        dates.sort()
        span_days = max(1, (dates[-1] - dates[0]).days + 1)
        latest = dates[-1]
        output.append(
            {
                "canonical_channel_id": channel,
                "message_count": len(dates),
                "first_published_at": dates[0],
                "last_published_at": latest,
                "posts_per_day_observed": len(dates) / span_days,
                "days_since_last_post": (now - latest).days,
            }
        )
    return output

