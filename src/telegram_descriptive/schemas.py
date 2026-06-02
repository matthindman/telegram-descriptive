"""Table contracts for the Telegram descriptive pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class ColumnSpec:
    """A minimal column contract independent of Spark-specific dtypes."""

    name: str
    kind: str = "any"
    nullable: bool = True
    description: str = ""


@dataclass(frozen=True)
class TableContract:
    """Expected grain, keys, and columns for a planned table."""

    name: str
    grain: str
    primary_key: tuple[str, ...]
    required_columns: tuple[ColumnSpec, ...]
    optional_columns: tuple[ColumnSpec, ...] = ()
    caveats: tuple[str, ...] = ()

    @property
    def required_names(self) -> tuple[str, ...]:
        return tuple(col.name for col in self.required_columns)

    @property
    def optional_names(self) -> tuple[str, ...]:
        return tuple(col.name for col in self.optional_columns)

    def validate_columns(self, columns: Iterable[str]) -> list[str]:
        observed = set(columns)
        return [name for name in self.required_names if name not in observed]

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "grain": self.grain,
            "primary_key": list(self.primary_key),
            "required_columns": [col.__dict__ for col in self.required_columns],
            "optional_columns": [col.__dict__ for col in self.optional_columns],
            "caveats": list(self.caveats),
        }


def c(name: str, kind: str = "any", nullable: bool = True, description: str = "") -> ColumnSpec:
    return ColumnSpec(name=name, kind=kind, nullable=nullable, description=description)


CONTRACTS: Mapping[str, TableContract] = {
    "silver_channels": TableContract(
        name="silver_channels",
        grain="one row per canonical public Telegram channel/group",
        primary_key=("canonical_channel_id",),
        required_columns=(
            c("canonical_channel_id", "string", False),
            c("channel_name", "string"),
            c("channel_url", "string"),
            c("detected_language", "string"),
            c("eligibility_status", "string"),
            c("latest_follower_count", "numeric"),
            c("first_observed_at", "timestamp"),
            c("last_observed_at", "timestamp"),
        ),
        optional_columns=(
            c("channel_type", "string"),
            c("public_status", "string"),
            c("source_provenance", "string"),
            c("quality_flags", "array<string>"),
        ),
        caveats=("follower_count semantics must be confirmed before headline member claims",),
    ),
    "silver_channel_metric_snapshots": TableContract(
        name="silver_channel_metric_snapshots",
        grain="one row per channel per selected metric snapshot policy",
        primary_key=("canonical_channel_id", "snapshot_policy", "snapshot_timestamp"),
        required_columns=(
            c("canonical_channel_id", "string", False),
            c("snapshot_policy", "string", False),
            c("snapshot_timestamp", "timestamp", False),
            c("follower_count", "numeric"),
            c("views_count", "numeric"),
            c("post_count", "numeric"),
            c("comment_count", "numeric"),
            c("like_count", "numeric"),
            c("share_count", "numeric"),
        ),
    ),
    "silver_messages": TableContract(
        name="silver_messages",
        grain="one row per ingested Telegram message/post",
        primary_key=("post_uid",),
        required_columns=(
            c("post_uid", "string", False),
            c("canonical_channel_id", "string", False),
            c("published_at", "timestamp"),
            c("post_type", "string"),
            c("text_for_lid", "string"),
            c("text_for_topics", "string"),
            c("has_text", "boolean"),
            c("is_forwarded", "boolean"),
            c("is_reply", "boolean"),
        ),
        optional_columns=(
            c("hashtags", "array<string>"),
            c("urls", "array<string>"),
            c("repost_channel_data", "string"),
            c("quality_flags", "array<string>"),
        ),
    ),
    "silver_post_metric_snapshots": TableContract(
        name="silver_post_metric_snapshots",
        grain="one row per post per selected metric snapshot policy",
        primary_key=("post_uid", "snapshot_policy", "snapshot_timestamp"),
        required_columns=(
            c("post_uid", "string", False),
            c("canonical_channel_id", "string", False),
            c("snapshot_policy", "string", False),
            c("snapshot_timestamp", "timestamp", False),
            c("post_view_count", "numeric"),
            c("post_share_count", "numeric"),
            c("post_comment_count", "numeric"),
            c("post_like_count", "numeric"),
            c("total_emoji_reactions", "numeric"),
        ),
    ),
    "silver_telegram_edges": TableContract(
        name="silver_telegram_edges",
        grain="one observed organic Telegram edge",
        primary_key=("edge_id",),
        required_columns=(
            c("edge_id", "string", False),
            c("source_channel_id", "string", False),
            c("target", "string", False),
            c("edge_type", "string", False),
            c("post_uid", "string"),
            c("observed_at", "timestamp"),
            c("is_artificial_crawl_edge", "boolean", False),
        ),
    ),
    "silver_random_walk_events": TableContract(
        name="silver_random_walk_events",
        grain="one crawl decision or transition event",
        primary_key=("crawl_run_id", "chain_id", "step_id"),
        required_columns=(
            c("crawl_run_id", "string", False),
            c("chain_id", "string", False),
            c("step_id", "integer", False),
            c("event_timestamp", "timestamp"),
            c("source_channel_id", "string"),
            c("followed_target", "string"),
            c("decision_type", "string"),
            c("restart_flag", "boolean"),
            c("validator_status", "string"),
        ),
        caveats=("Not visible as a clean production table in the 2026-06-01 probe.",),
    ),
    "silver_random_walk_exposures": TableContract(
        name="silver_random_walk_exposures",
        grain="one duplicate-collapsed eligible target exposure",
        primary_key=("crawl_run_id", "chain_id", "exposure_id"),
        required_columns=(
            c("crawl_run_id", "string", False),
            c("chain_id", "string", False),
            c("exposure_id", "string", False),
            c("target_channel_id", "string", False),
            c("exposure_timestamp", "timestamp"),
            c("eligible_flag", "boolean"),
            c("follower_count", "numeric"),
        ),
        caveats=("Required for discovery estimation; must not be fabricated from incomplete lineage.",),
    ),
    "silver_random_walk_validations": TableContract(
        name="silver_random_walk_validations",
        grain="one candidate Telegram handle or URL validation attempt",
        primary_key=("candidate_url", "validation_timestamp"),
        required_columns=(
            c("candidate_url", "string", False),
            c("normalized_username", "string"),
            c("validation_timestamp", "timestamp", False),
            c("is_public", "boolean"),
            c("is_broadcast_or_supergroup", "boolean"),
            c("follower_count", "numeric"),
            c("validation_status", "string"),
            c("failure_reason", "string"),
        ),
        caveats=("Not visible as a clean production table in the 2026-06-01 probe.",),
    ),
    "silver_ranked_metrics": TableContract(
        name="silver_ranked_metrics",
        grain="one channel per metric per ranking version",
        primary_key=("ranking_version", "metric_name", "rank"),
        required_columns=(
            c("ranking_version", "string", False),
            c("metric_name", "string", False),
            c("canonical_channel_id", "string", False),
            c("rank", "integer", False),
            c("metric_value", "numeric", False),
            c("snapshot_policy", "string"),
            c("snapshot_timestamp", "timestamp"),
        ),
    ),
    "silver_lid_segments": TableContract(
        name="silver_lid_segments",
        grain="one source-aware text segment submitted to language detection",
        primary_key=("lid_run_id", "segment_id"),
        required_columns=(
            c("lid_run_id", "string", False),
            c("segment_id", "string", False),
            c("entity_id", "string", False),
            c("entity_type", "string", False),
            c("source_field", "string", False),
            c("text", "string"),
            c("char_count", "integer"),
            c("token_count", "integer"),
            c("language", "string"),
            c("confidence", "numeric"),
            c("weight", "numeric"),
        ),
        caveats=("token_count is a rough whitespace diagnostic; char_count is preferred across scripts.",),
    ),
    "silver_topic_inputs": TableContract(
        name="silver_topic_inputs",
        grain="one compact channel or message evidence bundle submitted to topic classification",
        primary_key=("topic_run_id", "entity_id"),
        required_columns=(
            c("topic_run_id", "string", False),
            c("taxonomy_version", "string", False),
            c("entity_id", "string", False),
            c("entity_type", "string", False),
            c("evidence_bundle", "string", False),
            c("evidence_ids", "array<string>"),
            c("language_label", "string"),
        ),
    ),
    "gold_too_sample_frame": TableContract(
        name="gold_too_sample_frame",
        grain="one selected or candidate TOO channel",
        primary_key=("sample_version", "canonical_channel_id"),
        required_columns=(
            c("sample_version", "string", False),
            c("canonical_channel_id", "string", False),
            c("in_too_sample", "boolean", False),
            c("selection_rule", "string", False),
            c("rank", "integer"),
            c("metric_name", "string"),
            c("metric_value", "numeric"),
            c("coverage_estimate", "numeric"),
            c("coverage_lower_ci", "numeric"),
            c("post_ingestion_status", "string"),
        ),
    ),
    "gold_channel_analysis_frame": TableContract(
        name="gold_channel_analysis_frame",
        grain="one channel with descriptive covariates and labels",
        primary_key=("canonical_channel_id",),
        required_columns=(
            c("canonical_channel_id", "string", False),
            c("too_sample_version", "string"),
            c("follower_count", "numeric"),
            c("views_count", "numeric"),
            c("language_label", "string"),
            c("language_confidence", "numeric"),
            c("topic_label", "string"),
            c("topic_confidence", "numeric"),
            c("post_count", "numeric"),
            c("link_outdegree", "numeric"),
            c("forward_outdegree", "numeric"),
        ),
    ),
    "gold_message_analysis_frame": TableContract(
        name="gold_message_analysis_frame",
        grain="one ingested message with labels, engagement, and channel covariates",
        primary_key=("post_uid",),
        required_columns=(
            c("post_uid", "string", False),
            c("canonical_channel_id", "string", False),
            c("published_at", "timestamp"),
            c("content_type", "string"),
            c("post_view_count", "numeric"),
            c("language_label", "string"),
            c("topic_label", "string"),
            c("is_forwarded", "boolean"),
            c("has_text", "boolean"),
        ),
    ),
    "gold_population_estimates": TableContract(
        name="gold_population_estimates",
        grain="one estimate per run, metric, threshold, model, and parameter version",
        primary_key=("estimate_version", "estimand", "metric_name", "threshold", "model"),
        required_columns=(
            c("estimate_version", "string", False),
            c("estimand", "string", False),
            c("metric_name", "string", False),
            c("threshold", "numeric", False),
            c("model", "string", False),
            c("observed_n", "numeric"),
            c("estimate", "numeric"),
            c("lower_ci", "numeric"),
            c("upper_ci", "numeric"),
            c("diagnostic_flags", "array<string>"),
        ),
    ),
    "gold_validation_summaries": TableContract(
        name="gold_validation_summaries",
        grain="one validation summary row per run, task, cohort, and label where applicable",
        primary_key=("validation_run_id", "task", "cohort", "label"),
        required_columns=(
            c("validation_run_id", "string", False),
            c("task", "string", False),
            c("cohort", "string", False),
            c("label", "string", False),
            c("n_reviewed", "integer"),
            c("precision", "numeric"),
            c("recall", "numeric"),
            c("acceptance_status", "string"),
            c("notes", "string"),
        ),
    ),
}


def get_contract(name: str) -> TableContract:
    try:
        return CONTRACTS[name]
    except KeyError as exc:
        known = ", ".join(sorted(CONTRACTS))
        raise KeyError(f"Unknown contract {name!r}. Known contracts: {known}") from exc
