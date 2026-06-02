"""Exposure construction helpers."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from typing import Any


def exposure_id(crawl_run_id: Any, chain_id: Any, source: Any, target: Any, timestamp: Any) -> str:
    payload = f"{crawl_run_id}|{chain_id}|{source}|{target}|{timestamp}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def collapse_duplicate_exposures(
    exposures: Iterable[Mapping[str, Any]],
    key_fields: tuple[str, ...] = ("crawl_run_id", "chain_id", "target_channel_id"),
) -> list[dict[str, Any]]:
    """Keep the first exposure per key, preserving duplicate counts."""

    collapsed: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in exposures:
        key = tuple(row.get(field) for field in key_fields)
        if key not in collapsed:
            copied = dict(row)
            copied["duplicate_exposure_count"] = 1
            collapsed[key] = copied
        else:
            collapsed[key]["duplicate_exposure_count"] += 1
    return list(collapsed.values())

