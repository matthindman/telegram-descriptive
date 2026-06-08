"""Project configuration and table-name helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceTables:
    """Fully qualified source table defaults observed in the Telegram probe."""

    catalog: str = "prod_tads"
    telegram_schema: str = "telegram"
    random_walk_schema: str = "telegram_random_walk"
    too_schema: str = "telegram_too"
    channels: str = "tg_sl_channels"
    channel_metrics: str = "tg_sl_channels_metrics"
    posts: str = "tg_sl_posts"
    post_metrics: str = "tg_sl_posts_metrics"
    comments: str = "tg_sl_comments"
    comment_metrics: str = "tg_sl_comments_metrics"
    random_walk_ingest: str = "tg_bz_ingest"
    random_walk_ingest_log: str = "tg_bz_ingest_log"
    subsample_items: str = "subsample_items"
    post_embeddings: str = "post_embeddings"
    sampling_history: str = "sampling_history"

    def fqtn(self, schema: str, table: str) -> str:
        return f"{self.catalog}.{schema}.{table}"

    @property
    def too_channels(self) -> str:
        return self.fqtn(self.too_schema, self.channels)

    @property
    def too_channel_metrics(self) -> str:
        return self.fqtn(self.too_schema, self.channel_metrics)

    @property
    def too_posts(self) -> str:
        return self.fqtn(self.too_schema, self.posts)

    @property
    def too_post_metrics(self) -> str:
        return self.fqtn(self.too_schema, self.post_metrics)

    @property
    def random_walk_raw(self) -> str:
        return self.fqtn(self.random_walk_schema, self.random_walk_ingest)

    @property
    def random_walk_log(self) -> str:
        return self.fqtn(self.random_walk_schema, self.random_walk_ingest_log)

    @property
    def too_subsample_items(self) -> str:
        return self.fqtn(self.too_schema, self.subsample_items)

    @property
    def too_post_embeddings(self) -> str:
        return self.fqtn(self.too_schema, self.post_embeddings)

    @property
    def too_sampling_history(self) -> str:
        return self.fqtn(self.too_schema, self.sampling_history)


@dataclass(frozen=True)
class OutputTables:
    """Output table namespace and planned silver/gold table names."""

    catalog: str = "dev_sean"
    schema: str = "matt"
    prefix: str = "telegram_descriptive"

    planned_tables: tuple[str, ...] = (
        "silver_channels",
        "silver_channel_metric_snapshots",
        "silver_messages",
        "silver_post_metric_snapshots",
        "silver_telegram_edges",
        "silver_random_walk_events",
        "silver_random_walk_exposures",
        "silver_random_walk_validations",
        "silver_ranked_metrics",
        "silver_lid_segments",
        "silver_language_labels",
        "silver_topic_inputs",
        "silver_topic_labels",
        "gold_too_sample_frame",
        "gold_post_ingestion_audit",
        "gold_channel_analysis_frame",
        "gold_message_analysis_frame",
        "gold_population_estimates",
        "gold_tail_parameters",
        "gold_descriptive_summaries",
        "gold_network_summaries",
        "gold_robustness_summaries",
        "gold_reporting_manifest",
        "gold_validation_summaries",
    )

    def fqtn(self, name: str) -> str:
        return f"{self.catalog}.{self.schema}.{self.prefix}_{name}"

    def manifest(self) -> dict[str, str]:
        return {name: self.fqtn(name) for name in self.planned_tables}

    def governance_warnings(self) -> tuple[str, ...]:
        warnings: list[str] = []
        if self.catalog == "dev_sean" and self.schema == "matt":
            warnings.append(
                "Output namespace defaults to dev_sean.matt for development; switch to a governed "
                "shared catalog before publication-critical writes."
            )
        return tuple(warnings)


@dataclass(frozen=True)
class AnalysisConfig:
    """Configuration values that should not be magic constants in notebooks."""

    execution_mode: str = "manifest_only"
    run_id: str = "manual"
    sample_version: str = "telegram_too_v1"
    ranking_version: str = "telegram_rank_v1"
    estimate_version: str = "telegram_estimates_v1"
    lid_run_id: str = "telegram_lid_v1"
    topic_run_id: str = "telegram_topics_v1"
    random_seed: int = 20260602
    smoke_limit: int = 50_000
    write_outputs: bool = True
    metric_snapshot_policy: str = "latest"
    member_metric: str = "follower_count"
    channel_view_metric: str = "views_count"
    post_view_metric: str = "post_view_count"
    too_member_threshold: int = 10_000
    too_top_n: int = 1_662
    rank_boundaries: tuple[int, ...] = (50, 100, 200, 500, 1000)
    member_thresholds: tuple[int, ...] = (1_000, 10_000, 100_000, 1_000_000)
    top_n_values: tuple[int, ...] = (100, 500, 1000, 1662)
    bootstrap_replicates: int = 1000
    language_no_text_label: str = "NO TEXT"
    topic_taxonomy_version: str = "telegram_topics_v1"
    export_root: str = "/Volumes/dev_sean/matt/models/telegram_descriptive"

    @property
    def should_scan(self) -> bool:
        return self.execution_mode in {"smoke", "core", "full"}


@dataclass(frozen=True)
class ProjectConfig:
    """Top-level project configuration used by notebooks and tests."""

    sources: SourceTables = field(default_factory=SourceTables)
    outputs: OutputTables = field(default_factory=OutputTables)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def print_default_config() -> None:
    """CLI helper used by `telegram-descriptive`."""

    import json

    print(json.dumps(ProjectConfig().as_dict(), indent=2, sort_keys=True))
