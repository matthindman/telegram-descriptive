"""Engagement summary helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from statistics import median
from typing import Any


def safe_rate(numerator: Any, denominator: Any) -> float | None:
    if denominator is None:
        return None
    denominator = float(denominator)
    if denominator <= 0:
        return None
    return float(numerator or 0.0) / denominator


def engagement_summary(rows: Iterable[Mapping[str, Any]]) -> dict[str, float | None]:
    views: list[float] = []
    reaction_rates: list[float] = []
    share_rates: list[float] = []
    for row in rows:
        view_count = row.get("post_view_count")
        if view_count is not None:
            views.append(float(view_count))
        reaction_rate = safe_rate(row.get("total_emoji_reactions"), view_count)
        share_rate = safe_rate(row.get("post_share_count"), view_count)
        if reaction_rate is not None:
            reaction_rates.append(reaction_rate)
        if share_rate is not None:
            share_rates.append(share_rate)
    return {
        "post_count": len(views),
        "median_views": median(views) if views else None,
        "median_reactions_per_view": median(reaction_rates) if reaction_rates else None,
        "median_shares_per_view": median(share_rates) if share_rates else None,
    }

