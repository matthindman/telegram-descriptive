"""Exposure construction helpers."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from typing import Any


def exposure_id(crawl_run_id: Any, chain_id: Any, source: Any, target: Any, timestamp: Any) -> str:
    """Legacy event identifier retained for compatibility with older outputs."""

    payload = f"{crawl_run_id}|{chain_id}|{source}|{target}|{timestamp}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def source_visit_exposure_id(crawl_run_id: Any, batch_id: Any, target: Any) -> str:
    """Stable identifier at the documented source-visit exposure grain."""

    if any(value in (None, "") for value in (crawl_run_id, batch_id, target)):
        raise ValueError("crawl_run_id, batch_id, and target must be nonempty")
    payload = f"{crawl_run_id}|{batch_id}|{target}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def collapse_duplicate_exposures(
    exposures: Iterable[Mapping[str, Any]],
    key_fields: tuple[str, ...] = ("crawl_run_id", "batch_id", "target_channel_id"),
) -> list[dict[str, Any]]:
    """Collapse duplicate target mentions only within a source visit.

    The default key matches the crawler contract's unique
    ``(crawl_id, batch_id, target_channel)`` grain. Repeated exposure to the
    same target in another source visit, batch, or chain remains a separate
    record because that recurrence is essential for incidence estimation.
    """

    collapsed: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in exposures:
        missing = [field for field in key_fields if row.get(field) in (None, "")]
        if missing:
            raise ValueError(f"Exposure row is missing key fields: {missing}")
        key = tuple(row.get(field) for field in key_fields)
        if key not in collapsed:
            copied = dict(row)
            copied["duplicate_exposure_count"] = 1
            collapsed[key] = copied
        else:
            collapsed[key]["duplicate_exposure_count"] += 1
    return list(collapsed.values())
