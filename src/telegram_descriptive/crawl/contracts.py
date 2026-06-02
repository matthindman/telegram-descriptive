"""Contracts for random-walk source reconstruction."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrawlLineageRequirements:
    """Minimum inputs for defensible random-walk population estimation."""

    walk_events: tuple[str, ...] = (
        "crawl_run_id",
        "chain_id",
        "step_id",
        "timestamp",
        "candidate_targets",
        "followed_target",
        "decision_type",
    )
    validations: tuple[str, ...] = (
        "candidate_url",
        "normalized_username",
        "validation_timestamp",
        "is_public",
        "is_broadcast_or_supergroup",
        "follower_count",
    )
    exposures: tuple[str, ...] = (
        "crawl_run_id",
        "chain_id",
        "exposure_id",
        "target_channel_id",
        "eligible_flag",
    )


VISIBLE_RANDOM_WALK_BRONZE_COLUMNS = (
    "depth",
    "error",
    "id",
    "messages",
    "parentId",
    "status",
    "timestamp",
)


def visible_bronze_gap_summary(observed_columns: set[str] | None = None) -> dict[str, object]:
    """Summarize why the visible bronze table is not enough by itself."""

    observed = observed_columns or set(VISIBLE_RANDOM_WALK_BRONZE_COLUMNS)
    requirements = CrawlLineageRequirements()
    required = set(requirements.walk_events) | set(requirements.validations) | set(requirements.exposures)
    missing = sorted(required - observed)
    usable_parentage_fields = sorted(observed & {"depth", "id", "parentId", "timestamp", "status"})
    return {
        "status": "blocked" if missing else "available",
        "usable_parentage_fields": usable_parentage_fields,
        "missing_required_fields": missing,
        "warning": (
            "Do not treat parentId/depth as crawl lineage until their semantics are confirmed."
            if missing
            else ""
        ),
    }

