"""Diagnostics for reconstructed random-walk event tables."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from typing import Any


def transition_summary(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize chain sizes, decision types, and restart/walkback rates."""

    rows = list(events)
    by_chain: dict[Any, int] = defaultdict(int)
    decisions: Counter[str] = Counter()
    restarts = 0
    walkbacks = 0
    for row in rows:
        chain = row.get("chain_id", "unknown")
        by_chain[chain] += 1
        decisions[str(row.get("decision_type", "unknown"))] += 1
        restarts += bool(row.get("restart_flag"))
        walkbacks += bool(row.get("walkback_flag"))
    n = len(rows)
    return {
        "event_count": n,
        "chain_count": len(by_chain),
        "events_per_chain": dict(by_chain),
        "decision_counts": dict(decisions),
        "restart_rate": restarts / n if n else 0.0,
        "walkback_rate": walkbacks / n if n else 0.0,
    }


def discovery_timeline(exposures: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return cumulative unique eligible target discoveries by chain event order."""

    seen: set[Any] = set()
    timeline: list[dict[str, Any]] = []
    for idx, row in enumerate(exposures, start=1):
        if not row.get("eligible_flag", True):
            continue
        target = row.get("target_channel_id")
        if target is None:
            continue
        is_new = target not in seen
        seen.add(target)
        timeline.append(
            {
                "exposure_index": idx,
                "target_channel_id": target,
                "is_new_discovery": is_new,
                "cumulative_discoveries": len(seen),
            }
        )
    return timeline

