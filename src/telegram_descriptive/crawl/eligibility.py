"""Eligibility helpers for public Telegram channel/group frames."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


PUBLIC_TRUE = {"public", "true", "yes", "1", "open"}
PUBLIC_FALSE = {"private", "false", "no", "0", "deleted", "inaccessible"}


def normalize_public_status(value: Any) -> str:
    if value is None:
        return "unknown"
    text = str(value).strip().lower()
    if text in PUBLIC_TRUE:
        return "public"
    if text in PUBLIC_FALSE:
        return "not_public"
    return text or "unknown"


def eligibility_status(row: Mapping[str, Any], min_followers: int | None = None) -> str:
    """Classify candidate eligibility while preserving unknowns."""

    public_status = normalize_public_status(
        row.get("public_status") or row.get("is_public") or row.get("sourcing_status")
    )
    if public_status == "not_public":
        return "ineligible_not_public"
    follower_count = row.get("follower_count")
    if min_followers is not None and follower_count is not None:
        try:
            if float(follower_count) < min_followers:
                return "ineligible_below_threshold"
        except (TypeError, ValueError):
            return "unknown_bad_follower_count"
    if public_status == "unknown":
        return "unknown_public_status"
    return "eligible"

