"""Canonicalization helpers for planned Telegram silver/gold tables."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from typing import Any


def canonical_channel_id(value: Any) -> str | None:
    """Normalize Telegram channel IDs for joins across bigint/string source columns."""

    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "nan", "null"}:
        return None
    return text


def stable_edge_id(*parts: Any) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def rank_metric_rows(
    rows: Iterable[Mapping[str, Any]],
    channel_col: str,
    metric_col: str,
    ranking_version: str,
    metric_name: str | None = None,
) -> list[dict[str, Any]]:
    """Deduplicate and rank positive metric values descending."""

    by_channel: dict[str, float] = {}
    for row in rows:
        channel = canonical_channel_id(row.get(channel_col))
        value = row.get(metric_col)
        if channel is None or value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric < 0:
            continue
        by_channel[channel] = max(numeric, by_channel.get(channel, float("-inf")))

    ranked = sorted(by_channel.items(), key=lambda item: (-item[1], item[0]))
    return [
        {
            "ranking_version": ranking_version,
            "metric_name": metric_name or metric_col,
            "canonical_channel_id": channel,
            "rank": idx + 1,
            "metric_value": value,
        }
        for idx, (channel, value) in enumerate(ranked)
    ]

