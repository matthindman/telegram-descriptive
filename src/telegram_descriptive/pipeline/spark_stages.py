"""Spark implementations for the Telegram descriptive analysis stages.

The notebooks in this repository intentionally stay thin. This module contains
the end-to-end workflow logic: source reads, defensive schema handling,
canonical silver-table construction, estimator orchestration, descriptive
summaries, and durable writes. It is importable without PySpark so local unit
tests can still run, but every stage requires a Spark session at execution time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from telegram_descriptive.config import ProjectConfig
from telegram_descriptive.estimation.chao import chao2_from_counts
from telegram_descriptive.estimation.rank_tail import estimate_tail_ladder
from telegram_descriptive.io import spark_table_exists
from telegram_descriptive.schemas import TableContract, get_contract

try:  # pragma: no cover - exercised in Databricks, not local unit tests.
    from pyspark.sql import DataFrame, SparkSession, Window
    from pyspark.sql import functions as F
    from pyspark.sql import types as T
except Exception:  # pragma: no cover
    DataFrame = Any  # type: ignore
    SparkSession = Any  # type: ignore
    Window = None  # type: ignore
    F = None  # type: ignore
    T = None  # type: ignore


STAGE_NAMES = {
    "00": "data_inventory_and_contracts",
    "01": "crawl_qa_and_walk_diagnostics",
    "02": "discovery_population_estimation",
    "03": "rank_tail_denominators",
    "04": "too_sample_construction",
    "05": "post_ingestion_audit",
    "06": "language_detection",
    "06b": "language_validation_and_adjudication",
    "07": "topic_taxonomy_and_classification",
    "08": "channel_message_analysis_frame",
    "09": "audience_concentration_and_proxy_failure",
    "10": "content_posting_and_engagement",
    "11": "link_forwarding_networks",
    "12": "missed_audience_sensitivity",
    "13": "robustness_and_sensitivity",
    "14": "reporting_exports",
}


def _require_spark() -> None:
    if F is None or T is None or Window is None:
        raise RuntimeError("PySpark is required to run Telegram descriptive pipeline stages.")


@dataclass
class PipelineContext:
    spark: SparkSession
    config: ProjectConfig

    def source_exists(self, fqtn: str) -> bool:
        return spark_table_exists(self.spark, fqtn)

    def table(self, fqtn: str) -> DataFrame | None:
        if not self.source_exists(fqtn):
            return None
        df = self.spark.table(fqtn)
        if self.config.analysis.execution_mode == "smoke":
            return df.limit(self.config.analysis.smoke_limit)
        return df

    def target(self, name: str) -> str:
        return self.config.outputs.fqtn(name)

    def target_df(self, name: str) -> DataFrame | None:
        return self.table(self.target(name))

    def ensure_schema(self) -> None:
        self.spark.sql(f"CREATE SCHEMA IF NOT EXISTS {self.config.outputs.catalog}.{self.config.outputs.schema}")

    def write(self, name: str, df: DataFrame, replace_where: str | None = None) -> str:
        """Write a target table unless the run is manifest-only or writes are disabled."""

        target = self.target(name)
        if not self.config.analysis.should_scan or not self.config.analysis.write_outputs:
            return target
        self.ensure_schema()
        writer = df.write.format("delta").mode("overwrite")
        if replace_where and self.source_exists(target):
            writer = writer.option("replaceWhere", replace_where)
        writer.saveAsTable(target)
        return target


def _kind_to_spark_type(kind: str) -> Any:
    _require_spark()
    normalized = kind.lower()
    if normalized.startswith("array"):
        return T.ArrayType(T.StringType())
    if normalized in {"integer", "int"}:
        return T.IntegerType()
    if normalized in {"numeric", "float", "double"}:
        return T.DoubleType()
    if normalized == "boolean":
        return T.BooleanType()
    if normalized == "timestamp":
        return T.TimestampType()
    return T.StringType()


def _schema_for_contract(contract: TableContract) -> Any:
    _require_spark()
    fields = [
        T.StructField(col.name, _kind_to_spark_type(col.kind), col.nullable)
        for col in contract.required_columns + contract.optional_columns
    ]
    return T.StructType(fields)


def empty_contract_df(ctx: PipelineContext, name: str) -> DataFrame:
    return ctx.spark.createDataFrame([], _schema_for_contract(get_contract(name)))


def _source_manifest(config: ProjectConfig) -> dict[str, str]:
    sources = config.sources
    return {
        "too_channels": sources.too_channels,
        "too_channel_metrics": sources.too_channel_metrics,
        "too_posts": sources.too_posts,
        "too_post_metrics": sources.too_post_metrics,
        "too_subsample_items": sources.too_subsample_items,
        "too_post_embeddings": sources.too_post_embeddings,
        "too_sampling_history": sources.too_sampling_history,
        "random_walk_raw": sources.random_walk_raw,
        "random_walk_log": sources.random_walk_log,
    }


def _col(df: DataFrame, name: str, default: Any = None, cast: str | None = None) -> Any:
    _require_spark()
    expr = F.col(name) if name in df.columns else F.lit(default)
    return expr.cast(cast) if cast else expr


def _array_col(df: DataFrame, name: str) -> Any:
    _require_spark()
    if name not in df.columns:
        return _empty_string_array()
    dtype = dict(df.dtypes).get(name, "")
    if dtype.startswith("array"):
        return F.col(name).cast("array<string>")
    return F.array(F.col(name).cast("string"))


def _empty_string_array() -> Any:
    _require_spark()
    return F.expr("array()").cast("array<string>")


def _string_array(*exprs: Any) -> Any:
    _require_spark()
    return F.array(*[expr.cast("string") for expr in exprs])


def _compact_string_array(*exprs: Any) -> Any:
    _require_spark()
    array_expr = _string_array(*exprs)
    return F.filter(
        array_expr,
        lambda value: value.isNotNull() & (F.length(F.trim(value)) > 0),
    )


def _now_lit() -> Any:
    _require_spark()
    return F.lit(datetime.now(timezone.utc).isoformat()).cast("timestamp")


def _sql_literal(value: str) -> str:
    """Return a single-quoted SQL literal safe for Delta replaceWhere predicates."""

    return "'" + str(value).replace("'", "''") + "'"


def _quality_flags(*conditions: tuple[Any, str]) -> Any:
    _require_spark()
    arrays = [
        F.when(condition, F.array(F.lit(label))).otherwise(_empty_string_array())
        for condition, label in conditions
    ]
    if not arrays:
        return _empty_string_array()
    result = arrays[0]
    for array_expr in arrays[1:]:
        result = F.concat(result, array_expr)
    return result


def _validation_rows(ctx: PipelineContext, rows: list[dict[str, Any]]) -> DataFrame:
    _require_spark()
    schema = _schema_for_contract(get_contract("gold_validation_summaries"))
    normalized = []
    for row in rows:
        normalized.append(
            {
                "validation_run_id": row.get("validation_run_id", ctx.config.analysis.run_id),
                "task": row.get("task"),
                "cohort": row.get("cohort", "all"),
                "label": row.get("label", "all"),
                "n_reviewed": row.get("n_reviewed"),
                "precision": row.get("precision"),
                "recall": row.get("recall"),
                "acceptance_status": row.get("acceptance_status"),
                "notes": row.get("notes"),
            }
        )
    return ctx.spark.createDataFrame(normalized, schema)


def _summary_rows(ctx: PipelineContext, rows: list[dict[str, Any]]) -> DataFrame:
    _require_spark()
    schema = _schema_for_contract(get_contract("gold_descriptive_summaries"))
    normalized = []
    for row in rows:
        normalized.append(
            {
                "run_id": row.get("run_id", ctx.config.analysis.run_id),
                "section": row.get("section"),
                "cohort": row.get("cohort", "all"),
                "metric": row.get("metric"),
                "statistic": row.get("statistic"),
                "value": row.get("value"),
                "n": row.get("n"),
                "notes": row.get("notes"),
            }
        )
    return ctx.spark.createDataFrame(normalized, schema)


def _contract_select(df: DataFrame, contract_name: str) -> DataFrame:
    """Select required contract columns first, filling missing columns with nulls."""

    _require_spark()
    contract = get_contract(contract_name)
    contract_names = {spec.name for spec in contract.required_columns + contract.optional_columns}
    exprs = []
    for spec in contract.required_columns + contract.optional_columns:
        if spec.name in df.columns:
            exprs.append(F.col(spec.name).cast(_kind_to_spark_type(spec.kind)).alias(spec.name))
        else:
            exprs.append(F.lit(None).cast(_kind_to_spark_type(spec.kind)).alias(spec.name))
    extras = [F.col(col) for col in df.columns if col not in contract_names]
    return df.select(*exprs, *extras)


def _latest_by(df: DataFrame, partition_cols: list[str], order_cols: list[str]) -> DataFrame:
    _require_spark()
    order_exprs = [F.col(col).desc_nulls_last() for col in order_cols if col in df.columns]
    if not order_exprs:
        order_exprs = [F.lit(1)]
    window = Window.partitionBy(*partition_cols).orderBy(*order_exprs)
    return df.withColumn("_rn", F.row_number().over(window)).where(F.col("_rn") == 1).drop("_rn")


def _has_rows(df: DataFrame | None) -> bool:
    if df is None:
        return False
    return bool(df.limit(1).count())


def _build_channel_metric_snapshots(ctx: PipelineContext) -> DataFrame:
    metrics = ctx.table(ctx.config.sources.too_channel_metrics)
    if metrics is None:
        return empty_contract_df(ctx, "silver_channel_metric_snapshots")
    latest = _latest_by(
        metrics.withColumn("canonical_channel_id", F.col("channel_id").cast("string")),
        ["canonical_channel_id"],
        ["scrape_timestamp", "ingestion_timestamp"],
    )
    out = latest.select(
        F.col("canonical_channel_id"),
        F.lit(ctx.config.analysis.metric_snapshot_policy).alias("snapshot_policy"),
        _col(latest, "scrape_timestamp", cast="timestamp").alias("snapshot_timestamp"),
        _col(latest, "follower_count", cast="double").alias("follower_count"),
        _col(latest, "views_count", cast="double").alias("views_count"),
        _col(latest, "post_count", cast="double").alias("post_count"),
        _col(latest, "comment_count", cast="double").alias("comment_count"),
        _col(latest, "like_count", cast="double").alias("like_count"),
        _col(latest, "share_count", cast="double").alias("share_count"),
    )
    return _contract_select(out, "silver_channel_metric_snapshots")


def _build_silver_channels(ctx: PipelineContext, metric_snapshots: DataFrame) -> DataFrame:
    channels = ctx.table(ctx.config.sources.too_channels)
    if channels is None:
        return empty_contract_df(ctx, "silver_channels")
    latest_channels = _latest_by(
        channels.withColumn("canonical_channel_id", F.col("channel_id").cast("string")),
        ["canonical_channel_id"],
        ["scrape_timestamp", "last_ingestion_timestamp", "first_ingestion_timestamp"],
    )
    joined = latest_channels.join(metric_snapshots, "canonical_channel_id", "left")
    first_observed = F.least(
        _col(joined, "first_ingestion_timestamp", cast="timestamp"),
        _col(joined, "first_scrape_timestamp", cast="timestamp"),
    )
    last_observed = F.greatest(
        _col(joined, "last_ingestion_timestamp", cast="timestamp"),
        _col(joined, "scrape_timestamp", cast="timestamp"),
        _col(joined, "snapshot_timestamp", cast="timestamp"),
    )
    out = joined.select(
        F.col("canonical_channel_id"),
        _col(joined, "channel_name", cast="string").alias("channel_name"),
        _col(joined, "channel_url", cast="string").alias("channel_url"),
        _col(joined, "detected_language", cast="string").alias("detected_language"),
        F.when(F.col("canonical_channel_id").isNull(), F.lit("unknown_missing_id"))
        .otherwise(F.lit("eligible_unconfirmed_public_status"))
        .alias("eligibility_status"),
        _col(joined, "follower_count", cast="double").alias("latest_follower_count"),
        first_observed.alias("first_observed_at"),
        last_observed.alias("last_observed_at"),
        F.lit(None).cast("string").alias("channel_type"),
        F.lit("public_status_unverified").alias("public_status"),
        F.lit(ctx.config.sources.too_channels).alias("source_provenance"),
        _quality_flags(
            (F.col("canonical_channel_id").isNull(), "missing_channel_id"),
            (_col(joined, "follower_count").isNull(), "missing_follower_count"),
        ).alias("quality_flags"),
    )
    return _contract_select(out, "silver_channels")


def _build_post_metric_snapshots(ctx: PipelineContext) -> DataFrame:
    metrics = ctx.table(ctx.config.sources.too_post_metrics)
    if metrics is None:
        return empty_contract_df(ctx, "silver_post_metric_snapshots")
    latest = _latest_by(
        metrics.withColumn("canonical_channel_id", F.col("channel_id").cast("string")),
        ["post_uid"],
        ["scrape_timestamp", "ingestion_timestamp"],
    )
    out = latest.select(
        _col(latest, "post_uid", cast="string").alias("post_uid"),
        F.col("canonical_channel_id"),
        F.lit(ctx.config.analysis.metric_snapshot_policy).alias("snapshot_policy"),
        _col(latest, "scrape_timestamp", cast="timestamp").alias("snapshot_timestamp"),
        _col(latest, "post_view_count", cast="double").alias("post_view_count"),
        _col(latest, "post_share_count", cast="double").alias("post_share_count"),
        _col(latest, "post_comment_count", cast="double").alias("post_comment_count"),
        _col(latest, "post_like_count", cast="double").alias("post_like_count"),
        _col(latest, "total_emoji_reactions", cast="double").alias("total_emoji_reactions"),
    )
    return _contract_select(out, "silver_post_metric_snapshots")


def _build_silver_messages(ctx: PipelineContext) -> DataFrame:
    posts = ctx.table(ctx.config.sources.too_posts)
    if posts is None:
        return empty_contract_df(ctx, "silver_messages")
    base = posts.withColumn("canonical_channel_id", F.col("channel_id").cast("string"))
    text_expr = F.concat_ws(
        "\n",
        _col(base, "post_content", "").cast("string"),
        _col(base, "all_text", "").cast("string"),
        _col(base, "searchable_text", "").cast("string"),
        _col(base, "image_text", "").cast("string"),
        _col(base, "transcript_text", "").cast("string"),
    )
    out = base.select(
        _col(base, "post_uid", cast="string").alias("post_uid"),
        F.col("canonical_channel_id"),
        _col(base, "published_at", cast="timestamp").alias("published_at"),
        _col(base, "post_type", "unknown", "string").alias("post_type"),
        text_expr.alias("text_for_lid"),
        text_expr.alias("text_for_topics"),
        (F.length(F.trim(text_expr)) > 0).alias("has_text"),
        (_col(base, "shared_id").isNotNull() | _col(base, "repost_channel_data").isNotNull()).alias("is_forwarded"),
        (_col(base, "replied_id").isNotNull() | _col(base, "is_reply").cast("boolean")).alias("is_reply"),
        _array_col(base, "hashtags").alias("hashtags"),
        F.array_distinct(
            _compact_string_array(
                _col(base, "url", cast="string"),
                _col(base, "post_link", cast="string"),
                _col(base, "media_url", cast="string"),
            )
        ).alias("urls"),
        _col(base, "repost_channel_data", cast="string").alias("repost_channel_data"),
        _quality_flags(
            (_col(base, "post_uid").isNull(), "missing_post_uid"),
            (F.length(F.trim(text_expr)) == 0, "no_text"),
            (_col(base, "published_at").isNull(), "missing_published_at"),
        ).alias("quality_flags"),
        _col(base, "detected_language", cast="string").alias("detected_language"),
        _col(base, "is_ad", cast="boolean").alias("is_ad"),
        _col(base, "quoted_id", cast="string").alias("quoted_id"),
        _col(base, "replied_id", cast="string").alias("replied_id"),
        _col(base, "shared_id", cast="string").alias("shared_id"),
        _col(base, "root_post_id", cast="string").alias("root_post_id"),
    )
    return _contract_select(out, "silver_messages")


def stage_00(ctx: PipelineContext) -> dict[str, Any]:
    rows = []
    for logical_name, fqtn in _source_manifest(ctx.config).items():
        exists = ctx.source_exists(fqtn)
        columns: list[str] = []
        row_count: int | None = None
        if exists:
            df = ctx.spark.table(fqtn)
            columns = df.columns
            if ctx.config.analysis.should_scan:
                row_count = int(df.count()) if ctx.config.analysis.execution_mode != "smoke" else int(df.limit(ctx.config.analysis.smoke_limit).count())
        rows.append(
            {
                "artifact_name": f"source_table:{logical_name}",
                "artifact_type": "source_table",
                "source_table": fqtn,
                "row_count": row_count,
                "created_at_utc": datetime.now(timezone.utc),
                "notes": f"exists={exists}; columns={','.join(columns[:40])}",
            }
        )

    channel_metrics = _build_channel_metric_snapshots(ctx)
    channels = _build_silver_channels(ctx, channel_metrics)
    post_metrics = _build_post_metric_snapshots(ctx)
    messages = _build_silver_messages(ctx)
    ctx.write("silver_channel_metric_snapshots", channel_metrics)
    ctx.write("silver_channels", channels)
    ctx.write("silver_post_metric_snapshots", post_metrics)
    ctx.write("silver_messages", messages)

    manifest_schema = _schema_for_contract(get_contract("gold_reporting_manifest"))
    manifest_df = ctx.spark.createDataFrame(
        [
            {
                "run_id": ctx.config.analysis.run_id,
                **row,
            }
            for row in rows
        ],
        manifest_schema,
    )
    ctx.write(
        "gold_reporting_manifest",
        manifest_df,
        replace_where=f"run_id = {_sql_literal(ctx.config.analysis.run_id)} AND artifact_type = 'source_table'",
    )
    return {"stage": "00", "written": ["silver_channels", "silver_messages", "gold_reporting_manifest"]}


def _empty_random_walk_outputs(ctx: PipelineContext, reason: str) -> dict[str, Any]:
    ctx.write("silver_random_walk_events", empty_contract_df(ctx, "silver_random_walk_events"))
    if not ctx.source_exists(ctx.target("silver_random_walk_exposures")):
        ctx.write("silver_random_walk_exposures", empty_contract_df(ctx, "silver_random_walk_exposures"))
    if not ctx.source_exists(ctx.target("silver_random_walk_validations")):
        ctx.write("silver_random_walk_validations", empty_contract_df(ctx, "silver_random_walk_validations"))
    validations = _validation_rows(
        ctx,
        [
            {
                "task": "random_walk_lineage",
                "cohort": "all",
                "label": "blocked",
                "acceptance_status": "blocked_missing_lineage",
                "notes": reason,
            }
        ],
    )
    ctx.write("gold_validation_summaries", validations, replace_where=f"validation_run_id = {_sql_literal(ctx.config.analysis.run_id)} AND task = 'random_walk_lineage'")
    return {"status": "blocked", "reason": reason}


def stage_01(ctx: PipelineContext) -> dict[str, Any]:
    raw = ctx.table(ctx.config.sources.random_walk_raw)
    if raw is None:
        return _empty_random_walk_outputs(ctx, f"Missing source table {ctx.config.sources.random_walk_raw}")

    required = {"id", "parentId", "depth", "timestamp", "status"}
    missing = sorted(required - set(raw.columns))
    if missing:
        return _empty_random_walk_outputs(ctx, f"Random-walk bronze table lacks required audit columns: {missing}")

    events = raw.select(
        F.coalesce(_col(raw, "ingest_id", cast="string"), F.lit(ctx.config.analysis.run_id)).alias("crawl_run_id"),
        F.coalesce(_col(raw, "parentId", cast="string"), _col(raw, "id", cast="string"), F.lit("unknown")).alias("chain_id"),
        F.abs(F.hash(_col(raw, "id", cast="string"))).cast("int").alias("step_id"),
        _col(raw, "timestamp", cast="timestamp").alias("event_timestamp"),
        _col(raw, "channel_id", cast="string").alias("source_channel_id"),
        _col(raw, "parentId", cast="string").alias("followed_target"),
        F.lit("bronze_record_parentage_unconfirmed").alias("decision_type"),
        F.lit(False).alias("restart_flag"),
        _col(raw, "status", cast="string").alias("validator_status"),
        _col(raw, "depth", cast="int").alias("bronze_depth"),
        _col(raw, "error", cast="string").alias("bronze_error"),
        F.lit("parentId/depth semantics unconfirmed; not used for exposure estimation").alias("lineage_caveat"),
    )
    ctx.write("silver_random_walk_events", _contract_select(events, "silver_random_walk_events"))
    if not ctx.source_exists(ctx.target("silver_random_walk_exposures")):
        ctx.write("silver_random_walk_exposures", empty_contract_df(ctx, "silver_random_walk_exposures"))
    if not ctx.source_exists(ctx.target("silver_random_walk_validations")):
        ctx.write("silver_random_walk_validations", empty_contract_df(ctx, "silver_random_walk_validations"))
    validations = _validation_rows(
        ctx,
        [
            {
                "task": "random_walk_lineage",
                "cohort": "bronze_parentage",
                "label": "unconfirmed",
                "acceptance_status": "blocked_for_population_estimation",
                "notes": "Bronze parentage fields were materialized for QA only; exposures/validations remain unavailable.",
            }
        ],
    )
    ctx.write("gold_validation_summaries", validations, replace_where=f"validation_run_id = {_sql_literal(ctx.config.analysis.run_id)} AND task = 'random_walk_lineage'")
    return {"stage": "01", "written": ["silver_random_walk_events"], "population_estimation_blocked": True}


def stage_02(ctx: PipelineContext) -> dict[str, Any]:
    exposures = ctx.target_df("silver_random_walk_exposures")
    if exposures is None or not _has_rows(exposures):
        rows = [
            {
                "estimate_version": ctx.config.analysis.estimate_version,
                "estimand": "reachable_public_channel_count",
                "metric_name": "follower_count",
                "threshold": float(threshold),
                "model": "random_walk_gap",
                "observed_n": None,
                "estimate": None,
                "lower_ci": None,
                "upper_ci": None,
                "diagnostic_flags": ["missing_random_walk_exposures", "no_population_claim"],
            }
            for threshold in ctx.config.analysis.member_thresholds
        ]
        df = ctx.spark.createDataFrame(rows, _schema_for_contract(get_contract("gold_population_estimates")))
        ctx.write("gold_population_estimates", df, replace_where=f"estimate_version = {_sql_literal(ctx.config.analysis.estimate_version)} AND estimand = 'reachable_public_channel_count'")
        return {"stage": "02", "status": "gap_written"}

    eligible = exposures.where(F.col("eligible_flag") == F.lit(True))
    rows = []
    for threshold in ctx.config.analysis.member_thresholds:
        above = eligible.where(_col(eligible, "follower_count", cast="double") >= F.lit(float(threshold)))
        incidence = above.groupBy("target_channel_id").agg(F.countDistinct("chain_id").alias("chain_incidence"))
        summary = incidence.agg(
            F.count("*").alias("observed_n"),
            F.sum(F.when(F.col("chain_incidence") == 1, 1).otherwise(0)).alias("q1"),
            F.sum(F.when(F.col("chain_incidence") == 2, 1).otherwise(0)).alias("q2"),
        ).first()
        chains = above.agg(F.countDistinct("chain_id").alias("chains")).first()["chains"] or 0
        observed = float(summary["observed_n"] or 0)
        q1 = float(summary["q1"] or 0)
        q2 = float(summary["q2"] or 0)
        estimate = chao2_from_counts(
            samples=int(chains),
            observed_species=int(observed),
            singletons=int(q1),
            doubletons=int(q2),
        )
        rows.append(
            {
                "estimate_version": ctx.config.analysis.estimate_version,
                "estimand": "reachable_public_channel_count",
                "metric_name": "follower_count",
                "threshold": float(threshold),
                "model": "chao2_incidence",
                "observed_n": observed,
                "estimate": float(max(observed, estimate)),
                "lower_ci": observed,
                "upper_ci": None,
                "diagnostic_flags": [],
            }
        )
    df = ctx.spark.createDataFrame(rows, _schema_for_contract(get_contract("gold_population_estimates")))
    ctx.write("gold_population_estimates", df, replace_where=f"estimate_version = {_sql_literal(ctx.config.analysis.estimate_version)} AND estimand = 'reachable_public_channel_count'")
    return {"stage": "02", "status": "estimates_written"}


def _ranked_metrics(ctx: PipelineContext) -> DataFrame:
    metric_snapshots = ctx.target_df("silver_channel_metric_snapshots")
    post_metrics = ctx.target_df("silver_post_metric_snapshots")
    frames: list[DataFrame] = []
    if metric_snapshots is not None:
        for metric_name in (ctx.config.analysis.member_metric, ctx.config.analysis.channel_view_metric, "post_count"):
            if metric_name in metric_snapshots.columns:
                frames.append(
                    metric_snapshots.select(
                        F.lit(ctx.config.analysis.ranking_version).alias("ranking_version"),
                        F.lit(metric_name).alias("metric_name"),
                        F.col("canonical_channel_id"),
                        F.col(metric_name).cast("double").alias("metric_value"),
                        F.col("snapshot_policy"),
                        F.col("snapshot_timestamp"),
                    ).where(F.col("metric_value").isNotNull() & (F.col("metric_value") >= 0))
                )
    if post_metrics is not None:
        post_views = post_metrics.groupBy("canonical_channel_id").agg(
            F.sum("post_view_count").cast("double").alias("metric_value"),
            F.max("snapshot_timestamp").alias("snapshot_timestamp"),
        )
        frames.append(
            post_views.select(
                F.lit(ctx.config.analysis.ranking_version).alias("ranking_version"),
                F.lit("post_view_count_sum").alias("metric_name"),
                F.col("canonical_channel_id"),
                F.col("metric_value"),
                F.lit(ctx.config.analysis.metric_snapshot_policy).alias("snapshot_policy"),
                F.col("snapshot_timestamp"),
            ).where(F.col("metric_value").isNotNull() & (F.col("metric_value") >= 0))
        )
    if not frames:
        return empty_contract_df(ctx, "silver_ranked_metrics")
    ranked = frames[0]
    for frame in frames[1:]:
        ranked = ranked.unionByName(frame, allowMissingColumns=True)
    window = Window.partitionBy("ranking_version", "metric_name").orderBy(F.col("metric_value").desc_nulls_last(), F.col("canonical_channel_id"))
    return _contract_select(ranked.withColumn("rank", F.row_number().over(window)), "silver_ranked_metrics")


def stage_03(ctx: PipelineContext) -> dict[str, Any]:
    ranked = _ranked_metrics(ctx)
    ctx.write("silver_ranked_metrics", ranked)
    rows = []
    parameter_rows = []
    # Bounded driver collection: metric names and ranked channel values are at
    # channel-rank grain, not message grain. The Telegram TOO probe has 1,662
    # channels, so this is appropriate for the Python rank-tail estimator.
    for metric_name in [row["metric_name"] for row in ranked.select("metric_name").distinct().collect()]:
        metric_values = [
            float(row["metric_value"])
            for row in ranked.where(F.col("metric_name") == metric_name).orderBy("rank").select("metric_value").collect()
            if row["metric_value"] is not None
        ]
        for boundary in ctx.config.analysis.rank_boundaries:
            if len(metric_values) < max(boundary, 20):
                continue
            for estimate in estimate_tail_ladder(metric_values, boundary_rank=boundary, fitting_window=min(100, max(20, boundary // 2))):
                params = estimate.parameters
                rows.append(
                    {
                        "estimate_version": ctx.config.analysis.estimate_version,
                        "estimand": "audience_mass_denominator",
                        "metric_name": metric_name,
                        "threshold": float(boundary),
                        "model": f"rank_tail_{estimate.model}",
                        "observed_n": float(len(metric_values)),
                        "estimate": float(estimate.total_mass) if estimate.total_mass != float("inf") else None,
                        "lower_ci": float(estimate.observed_head_mass),
                        "upper_ci": None,
                        "diagnostic_flags": list(estimate.flags),
                    }
                )
                parameter_rows.append(
                    {
                        "estimate_version": ctx.config.analysis.estimate_version,
                        "metric_name": metric_name,
                        "boundary_rank": int(boundary),
                        "model": f"rank_tail_{estimate.model}",
                        "y0": float(params.y0),
                        "alpha0": float(params.alpha0),
                        "eta0": float(params.eta0),
                        "eta1": float(params.eta1),
                        "eta2": float(params.eta2),
                        "fitting_window": int(params.fitting_window),
                        "observed_head_mass": float(estimate.observed_head_mass),
                        "tail_mass": float(estimate.tail_mass) if estimate.tail_mass != float("inf") else None,
                        "total_mass": float(estimate.total_mass) if estimate.total_mass != float("inf") else None,
                        "diagnostic_flags": list(estimate.flags),
                    }
                )
    if rows:
        df = ctx.spark.createDataFrame(rows, _schema_for_contract(get_contract("gold_population_estimates")))
        ctx.write("gold_population_estimates", df, replace_where=f"estimate_version = {_sql_literal(ctx.config.analysis.estimate_version)} AND estimand = 'audience_mass_denominator'")
    if parameter_rows:
        params_df = ctx.spark.createDataFrame(parameter_rows, _schema_for_contract(get_contract("gold_tail_parameters")))
        ctx.write("gold_tail_parameters", params_df, replace_where=f"estimate_version = {_sql_literal(ctx.config.analysis.estimate_version)}")
    return {"stage": "03", "ranked_metrics": ranked.count() if ctx.config.analysis.should_scan else None, "tail_rows": len(rows)}


def stage_04(ctx: PipelineContext) -> dict[str, Any]:
    ranked = ctx.target_df("silver_ranked_metrics")
    if ranked is None:
        ctx.write("gold_too_sample_frame", empty_contract_df(ctx, "gold_too_sample_frame"))
        return {"stage": "04", "status": "missing_ranked_metrics"}
    metric = ctx.config.analysis.member_metric
    selected = ranked.where(F.col("metric_name") == metric).withColumn(
        "in_too_sample",
        (F.col("rank") <= F.lit(ctx.config.analysis.too_top_n))
        | (F.col("metric_value") >= F.lit(float(ctx.config.analysis.too_member_threshold))),
    )
    numerator = selected.where("in_too_sample").agg(F.sum("metric_value").alias("numerator_mass")).first()["numerator_mass"]
    estimates = ctx.target_df("gold_population_estimates")
    denominator = None
    if estimates is not None:
        row = (
            estimates.where(
                (F.col("estimand") == "audience_mass_denominator")
                & (F.col("metric_name") == metric)
                & (F.col("model") == "rank_tail_D0")
            )
            .orderBy(F.col("threshold").asc())
            .select("estimate")
            .first()
        )
        denominator = row["estimate"] if row else None
    coverage_expr = F.lit(float(numerator) / float(denominator)).cast("double") if numerator and denominator else F.lit(None).cast("double")
    out = selected.select(
        F.lit(ctx.config.analysis.sample_version).alias("sample_version"),
        F.col("canonical_channel_id"),
        F.col("in_too_sample"),
        F.concat(F.lit("rank<="), F.lit(ctx.config.analysis.too_top_n), F.lit(" OR "), F.lit(metric), F.lit(">="), F.lit(ctx.config.analysis.too_member_threshold)).alias("selection_rule"),
        F.col("rank"),
        F.col("metric_name"),
        F.col("metric_value"),
        coverage_expr.alias("coverage_estimate"),
        coverage_expr.alias("coverage_lower_ci"),
        F.lit("pending_post_ingestion_audit").alias("post_ingestion_status"),
    )
    ctx.write("gold_too_sample_frame", _contract_select(out, "gold_too_sample_frame"))
    return {"stage": "04", "sample_rows": out.count() if ctx.config.analysis.should_scan else None}


def stage_05(ctx: PipelineContext) -> dict[str, Any]:
    sample = ctx.target_df("gold_too_sample_frame")
    messages = ctx.target_df("silver_messages")
    post_metrics = ctx.target_df("silver_post_metric_snapshots")
    if sample is None or messages is None:
        ctx.write("gold_post_ingestion_audit", empty_contract_df(ctx, "gold_post_ingestion_audit"))
        return {"stage": "05", "status": "missing_inputs"}
    msg_summary = messages.groupBy("canonical_channel_id").agg(
        F.count("*").cast("int").alias("observed_message_count"),
        F.min("published_at").alias("first_published_at"),
        F.max("published_at").alias("last_published_at"),
    )
    metric_channels = (
        post_metrics.select("canonical_channel_id").distinct().withColumn("post_metrics_available", F.lit(True))
        if post_metrics is not None
        else ctx.spark.createDataFrame([], "canonical_channel_id string, post_metrics_available boolean")
    )
    joined = sample.join(msg_summary, "canonical_channel_id", "left").join(metric_channels, "canonical_channel_id", "left")
    out = joined.select(
        F.col("sample_version"),
        F.col("canonical_channel_id"),
        F.col("in_too_sample").alias("expected_in_sample"),
        F.coalesce(F.col("observed_message_count"), F.lit(0)).cast("int").alias("observed_message_count"),
        F.col("first_published_at"),
        F.col("last_published_at"),
        F.coalesce(F.col("post_metrics_available"), F.lit(False)).alias("post_metrics_available"),
        F.when(F.coalesce(F.col("observed_message_count"), F.lit(0)) > 0, F.lit("observed_messages"))
        .otherwise(F.lit("missing_messages"))
        .alias("post_ingestion_status"),
        _quality_flags(
            (F.coalesce(F.col("observed_message_count"), F.lit(0)) == 0, "missing_messages"),
            (F.col("post_metrics_available").isNull(), "missing_post_metrics"),
        ).alias("audit_flags"),
    )
    ctx.write("gold_post_ingestion_audit", _contract_select(out, "gold_post_ingestion_audit"))
    return {"stage": "05", "audit_rows": out.count() if ctx.config.analysis.should_scan else None}


def _segments_for(ctx: PipelineContext, df: DataFrame, entity_type: str, entity_col: str, fields: list[tuple[str, float]]) -> DataFrame:
    structs = []
    for field, weight in fields:
        structs.append(
            F.struct(
                F.lit(field).alias("source_field"),
                _col(df, field, "").cast("string").alias("text"),
                F.lit(float(weight)).alias("weight"),
            )
        )
    exploded = df.select(
        _col(df, entity_col, cast="string").alias("entity_id"),
        F.lit(entity_type).alias("entity_type"),
        _col(df, "detected_language", cast="string").alias("detected_language"),
        F.explode(F.array(*structs)).alias("segment"),
    )
    return exploded.select(
        F.lit(ctx.config.analysis.lid_run_id).alias("lid_run_id"),
        F.sha2(F.concat_ws(":", F.col("entity_type"), F.col("entity_id"), F.col("segment.source_field")), 256).alias("segment_id"),
        F.col("entity_id"),
        F.col("entity_type"),
        F.col("segment.source_field").alias("source_field"),
        F.trim(F.col("segment.text")).alias("text"),
        F.length(F.trim(F.col("segment.text"))).cast("int").alias("char_count"),
        F.size(F.split(F.trim(F.col("segment.text")), r"\s+")).cast("int").alias("token_count"),
        F.coalesce(F.col("detected_language"), F.when(F.length(F.trim(F.col("segment.text"))) == 0, F.lit("NO TEXT")).otherwise(F.lit("UNKNOWN"))).alias("language"),
        F.when(F.col("detected_language").isNotNull(), F.lit(0.7)).otherwise(F.lit(0.2)).cast("double").alias("confidence"),
        F.col("segment.weight").cast("double").alias("weight"),
    ).where(F.col("entity_id").isNotNull())


def stage_06(ctx: PipelineContext) -> dict[str, Any]:
    channels = ctx.target_df("silver_channels")
    messages = ctx.target_df("silver_messages")
    frames: list[DataFrame] = []
    if channels is not None:
        frames.append(_segments_for(ctx, channels, "channel", "canonical_channel_id", [("channel_name", 0.8), ("detected_language", 0.2)]))
    if messages is not None:
        frames.append(_segments_for(ctx, messages, "message", "post_uid", [("text_for_lid", 1.0), ("detected_language", 0.2)]))
    if not frames:
        ctx.write("silver_lid_segments", empty_contract_df(ctx, "silver_lid_segments"))
        ctx.write("silver_language_labels", empty_contract_df(ctx, "silver_language_labels"))
        return {"stage": "06", "status": "missing_inputs"}
    segments = frames[0]
    for frame in frames[1:]:
        segments = segments.unionByName(frame, allowMissingColumns=True)
    segments = _contract_select(segments.where(F.col("char_count") >= 1), "silver_lid_segments")
    ctx.write("silver_lid_segments", segments)
    scores = segments.groupBy("entity_type", "entity_id", "language").agg(
        F.sum(F.col("confidence") * F.col("weight")).alias("score"),
        F.count("*").alias("segment_count"),
        F.sum("weight").alias("evidence_weight"),
    )
    window = Window.partitionBy("entity_type", "entity_id").orderBy(F.col("score").desc_nulls_last(), F.col("language"))
    top = scores.withColumn("rn", F.row_number().over(window)).where("rn = 1")
    totals = scores.groupBy("entity_type", "entity_id").agg(F.sum("score").alias("total_score"), F.count("*").alias("label_count"))
    labels = top.join(totals, ["entity_type", "entity_id"], "left").select(
        F.lit(ctx.config.analysis.lid_run_id).alias("lid_run_id"),
        F.col("entity_type"),
        F.col("entity_id"),
        F.when(F.col("total_score") <= 0, F.lit("NO TEXT")).otherwise(F.col("language")).alias("language_label"),
        F.lit(None).cast("double").alias("language_confidence"),
        F.lit(None).cast("double").alias("language_margin"),
        F.col("evidence_weight").cast("double").alias("language_evidence_weight"),
        F.col("segment_count").cast("int").alias("language_segment_count"),
        F.lit("source_detected_language_or_text_presence").alias("label_source"),
    )
    ctx.write("silver_language_labels", _contract_select(labels, "silver_language_labels"))
    return {"stage": "06", "segments": segments.count() if ctx.config.analysis.should_scan else None}


def stage_06b(ctx: PipelineContext) -> dict[str, Any]:
    labels = ctx.target_df("silver_language_labels")
    if labels is None:
        validations = _validation_rows(ctx, [{"task": "language_validation", "label": "missing_labels", "acceptance_status": "blocked", "notes": "silver_language_labels missing"}])
    else:
        # Bounded driver collection: one row per entity type/language label.
        counts = labels.groupBy("entity_type", "language_label").agg(F.count("*").alias("n")).collect()
        validations = _validation_rows(
            ctx,
            [
                {
                    "task": "language_validation",
                    "cohort": row["entity_type"],
                    "label": row["language_label"],
                    "n_reviewed": int(row["n"]),
                    "acceptance_status": "requires_manual_validation",
                    "notes": "Pipeline labels are provisional until adjudicated review labels are supplied.",
                }
                for row in counts
            ],
        )
    ctx.write("gold_validation_summaries", validations, replace_where=f"validation_run_id = {_sql_literal(ctx.config.analysis.run_id)} AND task = 'language_validation'")
    return {"stage": "06b", "status": "validation_summary_written"}


TOPIC_RULES = {
    "crypto_finance": ("crypto", "bitcoin", "trading", "forex", "investment"),
    "health": ("health", "medical", "doctor", "covid", "vaccine"),
    "geopolitics_war": ("war", "military", "frontline", "missile", "army"),
    "news_politics": ("news", "politics", "election", "government", "parliament"),
    "commerce": ("shop", "sale", "discount", "marketplace", "order"),
    "file_sharing": ("download", "apk", "pdf", "leak", "torrent"),
    "education": ("course", "lesson", "exam", "school", "university"),
    "technology": ("software", "ai", "cyber", "developer", "programming"),
}


TOPIC_LABELS = {
    "crypto_finance": "Crypto / finance",
    "health": "Health",
    "geopolitics_war": "Geopolitics / war",
    "news_politics": "News / politics",
    "commerce": "Commerce",
    "file_sharing": "File sharing",
    "education": "Education",
    "technology": "Technology",
    "mixed_unknown": "Mixed / unknown",
}


def _topic_expr(evidence_col: str = "evidence_bundle") -> Any:
    expr = F.lit("mixed_unknown")
    lower = F.lower(F.col(evidence_col))
    for topic, keywords in TOPIC_RULES.items():
        condition = None
        for keyword in keywords:
            condition = lower.contains(keyword) if condition is None else (condition | lower.contains(keyword))
        expr = F.when(condition, F.lit(topic)).otherwise(expr)
    return expr


def stage_07(ctx: PipelineContext) -> dict[str, Any]:
    channels = ctx.target_df("silver_channels")
    messages = ctx.target_df("silver_messages")
    language = ctx.target_df("silver_language_labels")
    if channels is None:
        ctx.write("silver_topic_inputs", empty_contract_df(ctx, "silver_topic_inputs"))
        ctx.write("silver_topic_labels", empty_contract_df(ctx, "silver_topic_labels"))
        return {"stage": "07", "status": "missing_channels"}
    if messages is not None:
        sample_window = Window.partitionBy("canonical_channel_id").orderBy(
            F.col("published_at").desc_nulls_last(),
            F.col("post_uid").asc_nulls_last(),
        )
        bounded_messages = (
            messages.where(F.col("has_text") == F.lit(True))
            .withColumn("_topic_sample_rank", F.row_number().over(sample_window))
            .where(F.col("_topic_sample_rank") <= 12)
        )
        # Bounded aggregation: at most 12 messages per channel reach collect_list.
        msg_samples = bounded_messages.groupBy("canonical_channel_id").agg(
            F.collect_list(F.substring("text_for_topics", 1, 500)).alias("message_samples"),
            F.collect_list("post_uid").alias("evidence_ids"),
        )
    else:
        msg_samples = ctx.spark.createDataFrame([], "canonical_channel_id string, message_samples array<string>, evidence_ids array<string>")
    lang = (
        language.where(F.col("entity_type") == "channel").select(F.col("entity_id").alias("canonical_channel_id"), "language_label")
        if language is not None
        else ctx.spark.createDataFrame([], "canonical_channel_id string, language_label string")
    )
    joined = channels.join(msg_samples, "canonical_channel_id", "left").join(lang, "canonical_channel_id", "left")
    evidence = F.concat_ws(
        "\n",
        F.concat(F.lit("title: "), F.coalesce(F.col("channel_name"), F.lit(""))),
        F.concat(F.lit("url: "), F.coalesce(F.col("channel_url"), F.lit(""))),
        F.concat_ws("\n", F.coalesce(F.col("message_samples"), _empty_string_array())),
    )
    inputs = joined.select(
        F.lit(ctx.config.analysis.topic_run_id).alias("topic_run_id"),
        F.lit(ctx.config.analysis.topic_taxonomy_version).alias("taxonomy_version"),
        F.col("canonical_channel_id").alias("entity_id"),
        F.lit("channel").alias("entity_type"),
        evidence.alias("evidence_bundle"),
        F.coalesce(F.col("evidence_ids"), _empty_string_array()).alias("evidence_ids"),
        F.col("language_label"),
    )
    ctx.write("silver_topic_inputs", _contract_select(inputs, "silver_topic_inputs"))
    topic_key = _topic_expr()
    labels = inputs.withColumn("topic_key", topic_key)
    label_map = F.create_map(*[item for pair in TOPIC_LABELS.items() for item in (F.lit(pair[0]), F.lit(pair[1]))])
    topic_labels = labels.select(
        F.col("topic_run_id"),
        F.col("taxonomy_version"),
        F.col("entity_id"),
        F.col("entity_type"),
        F.col("topic_key"),
        F.coalesce(F.element_at(label_map, F.col("topic_key")), F.lit("Mixed / unknown")).alias("topic_label"),
        F.lit(None).cast("double").alias("topic_confidence"),
        F.lit("multilingual_keyword_fallback_requires_validation").alias("classification_method"),
        F.col("evidence_ids"),
    )
    ctx.write("silver_topic_labels", _contract_select(topic_labels, "silver_topic_labels"))
    return {"stage": "07", "topic_inputs": inputs.count() if ctx.config.analysis.should_scan else None}


def stage_08(ctx: PipelineContext) -> dict[str, Any]:
    channels = ctx.target_df("silver_channels")
    messages = ctx.target_df("silver_messages")
    channel_metrics = ctx.target_df("silver_channel_metric_snapshots")
    post_metrics = ctx.target_df("silver_post_metric_snapshots")
    sample = ctx.target_df("gold_too_sample_frame")
    audit = ctx.target_df("gold_post_ingestion_audit")
    language = ctx.target_df("silver_language_labels")
    topics = ctx.target_df("silver_topic_labels")
    edges = ctx.target_df("silver_telegram_edges")
    if channels is None:
        ctx.write("gold_channel_analysis_frame", empty_contract_df(ctx, "gold_channel_analysis_frame"))
        ctx.write("gold_message_analysis_frame", empty_contract_df(ctx, "gold_message_analysis_frame"))
        return {"stage": "08", "status": "missing_channels"}
    channel_metrics_ch = (
        channel_metrics.select(
            "canonical_channel_id",
            F.col("follower_count").cast("double").alias("follower_count"),
            F.col("views_count").cast("double").alias("views_count"),
            F.col("post_count").cast("double").alias("post_count"),
        )
        if channel_metrics is not None
        else ctx.spark.createDataFrame(
            [],
            "canonical_channel_id string, follower_count double, views_count double, post_count double",
        )
    )
    sample_ch = (
        sample.select("canonical_channel_id", F.col("sample_version").alias("sample_version"))
        if sample is not None
        else ctx.spark.createDataFrame([], "canonical_channel_id string, sample_version string")
    )
    audit_ch = (
        audit.select(
            "canonical_channel_id",
            F.col("observed_message_count").cast("double").alias("observed_message_count"),
        )
        if audit is not None
        else ctx.spark.createDataFrame([], "canonical_channel_id string, observed_message_count double")
    )
    lang_ch = (
        language.where(F.col("entity_type") == "channel").select(F.col("entity_id").alias("canonical_channel_id"), "language_label", "language_confidence")
        if language is not None
        else ctx.spark.createDataFrame([], "canonical_channel_id string, language_label string, language_confidence double")
    )
    topic_ch = (
        topics.where(F.col("entity_type") == "channel").select(F.col("entity_id").alias("canonical_channel_id"), "topic_label", "topic_confidence")
        if topics is not None
        else ctx.spark.createDataFrame([], "canonical_channel_id string, topic_label string, topic_confidence double")
    )
    degrees = (
        edges.groupBy("source_channel_id")
        .agg(
            F.sum(F.when(F.col("edge_type") == "url_link", 1).otherwise(0)).cast("double").alias("link_outdegree"),
            F.sum(F.when(F.col("edge_type").isin("forwarded_from", "quoted_post", "reply_to"), 1).otherwise(0)).cast("double").alias("forward_outdegree"),
        )
        .withColumnRenamed("source_channel_id", "canonical_channel_id")
        if edges is not None
        else ctx.spark.createDataFrame([], "canonical_channel_id string, link_outdegree double, forward_outdegree double")
    )
    frame = channels.join(channel_metrics_ch, "canonical_channel_id", "left")
    for optional in (sample_ch, audit_ch, lang_ch, topic_ch, degrees):
        frame = frame.join(optional, "canonical_channel_id", "left")
    channel_out = frame.select(
        F.col("canonical_channel_id"),
        F.coalesce(F.col("sample_version"), F.lit(ctx.config.analysis.sample_version)).alias("too_sample_version"),
        F.coalesce(F.col("follower_count"), F.col("latest_follower_count")).cast("double").alias("follower_count"),
        F.col("views_count").cast("double").alias("views_count"),
        F.coalesce(F.col("language_label"), F.col("detected_language")).alias("language_label"),
        F.col("language_confidence").cast("double").alias("language_confidence"),
        F.col("topic_label"),
        F.col("topic_confidence").cast("double").alias("topic_confidence"),
        F.coalesce(F.col("post_count"), F.col("observed_message_count")).cast("double").alias("post_count"),
        F.coalesce(F.col("link_outdegree"), F.lit(0.0)).alias("link_outdegree"),
        F.coalesce(F.col("forward_outdegree"), F.lit(0.0)).alias("forward_outdegree"),
    )
    ctx.write("gold_channel_analysis_frame", _contract_select(channel_out, "gold_channel_analysis_frame"))
    if messages is None:
        ctx.write("gold_message_analysis_frame", empty_contract_df(ctx, "gold_message_analysis_frame"))
    else:
        msg = messages
        if post_metrics is not None:
            msg = msg.join(post_metrics.select("post_uid", "post_view_count"), "post_uid", "left")
        msg_lang = (
            language.where(F.col("entity_type") == "message").select(F.col("entity_id").alias("post_uid"), F.col("language_label").alias("message_language_label"))
            if language is not None
            else ctx.spark.createDataFrame([], "post_uid string, message_language_label string")
        )
        msg = msg.join(msg_lang, "post_uid", "left").join(channel_out.select("canonical_channel_id", F.col("language_label").alias("channel_language_label"), "topic_label"), "canonical_channel_id", "left")
        message_out = msg.select(
            F.col("post_uid"),
            F.col("canonical_channel_id"),
            F.col("published_at"),
            F.col("post_type").alias("content_type"),
            F.col("post_view_count").cast("double"),
            F.coalesce(F.col("message_language_label"), F.col("channel_language_label"), F.col("detected_language")).alias("language_label"),
            F.col("topic_label"),
            F.col("is_forwarded"),
            F.col("has_text"),
        )
        ctx.write("gold_message_analysis_frame", _contract_select(message_out, "gold_message_analysis_frame"))
    return {"stage": "08", "status": "frames_written"}


def _metric_summary_rows(df: DataFrame, section: str, metrics: list[str], run_id: str) -> DataFrame:
    rows = []
    for metric in metrics:
        if metric not in df.columns:
            continue
        stats = df.agg(
            F.count(metric).alias("n"),
            F.mean(metric).alias("mean"),
            F.expr(f"percentile_approx({metric}, 0.5)").alias("median"),
            F.max(metric).alias("max"),
            F.sum(metric).alias("sum"),
        ).first()
        for stat in ("mean", "median", "max", "sum"):
            rows.append(
                {
                    "run_id": run_id,
                    "section": section,
                    "cohort": "all",
                    "metric": metric,
                    "statistic": stat,
                    "value": float(stats[stat]) if stats[stat] is not None else None,
                    "n": int(stats["n"] or 0),
                    "notes": None,
                }
            )
    return df.sparkSession.createDataFrame(rows, _schema_for_contract(get_contract("gold_descriptive_summaries")))


def stage_09(ctx: PipelineContext) -> dict[str, Any]:
    frame = ctx.target_df("gold_channel_analysis_frame")
    if frame is None:
        out = _summary_rows(ctx, [{"section": "audience", "metric": "missing_input", "statistic": "status", "value": None, "notes": "gold_channel_analysis_frame missing"}])
    else:
        out = _metric_summary_rows(frame, "audience", ["follower_count", "views_count", "post_count", "link_outdegree", "forward_outdegree"], ctx.config.analysis.run_id)
    ctx.write("gold_descriptive_summaries", out, replace_where=f"run_id = {_sql_literal(ctx.config.analysis.run_id)} AND section = 'audience'")
    return {"stage": "09", "status": "audience_summaries_written"}


def stage_10(ctx: PipelineContext) -> dict[str, Any]:
    messages = ctx.target_df("gold_message_analysis_frame")
    if messages is None:
        out = _summary_rows(ctx, [{"section": "content", "metric": "missing_input", "statistic": "status", "value": None, "notes": "gold_message_analysis_frame missing"}])
    else:
        # Bounded driver collection: one row per content type, after Spark aggregation.
        content_counts = messages.groupBy("content_type").agg(F.count("*").alias("n"), F.mean("post_view_count").alias("mean_views")).collect()
        rows = [
            {
                "section": "content",
                "cohort": row["content_type"] or "unknown",
                "metric": "messages",
                "statistic": "count",
                "value": float(row["n"]),
                "n": int(row["n"]),
                "notes": None,
            }
            for row in content_counts
        ]
        rows.extend(
            {
                "section": "content",
                "cohort": row["content_type"] or "unknown",
                "metric": "post_view_count",
                "statistic": "mean",
                "value": float(row["mean_views"]) if row["mean_views"] is not None else None,
                "n": int(row["n"]),
                "notes": None,
            }
            for row in content_counts
        )
        out = _summary_rows(ctx, rows)
    ctx.write("gold_descriptive_summaries", out, replace_where=f"run_id = {_sql_literal(ctx.config.analysis.run_id)} AND section = 'content'")
    return {"stage": "10", "status": "content_summaries_written"}


def _domain_expr(normalized_url_col: str) -> Any:
    host = F.lower(
        F.regexp_extract(
            F.col(normalized_url_col),
            r"^[A-Za-z][A-Za-z0-9+.-]*://(?:[^/@?#]+@)?([^/:?#]+)",
            1,
        )
    )
    return F.regexp_replace(host, r"^www\.", "")


def stage_11(ctx: PipelineContext) -> dict[str, Any]:
    messages = ctx.target_df("silver_messages")
    if messages is None:
        ctx.write("silver_telegram_edges", empty_contract_df(ctx, "silver_telegram_edges"))
        ctx.write("gold_network_summaries", empty_contract_df(ctx, "gold_network_summaries"))
        return {"stage": "11", "status": "missing_messages"}
    url_candidates = messages.select(
        F.col("canonical_channel_id").alias("source_channel_id"),
        F.col("post_uid"),
        F.explode_outer("urls").alias("url"),
        F.col("published_at").alias("observed_at"),
    ).where(F.col("url").isNotNull()).withColumn(
        "normalized_url",
        F.when(F.col("url").rlike(r"^[A-Za-z][A-Za-z0-9+.-]*://"), F.col("url")).otherwise(F.concat(F.lit("https://"), F.col("url"))),
    )
    url_edges = url_candidates.select(
        F.sha2(F.concat_ws(":", "source_channel_id", "post_uid", "normalized_url", F.lit("url_link")), 256).alias("edge_id"),
        F.col("source_channel_id"),
        _domain_expr("normalized_url").alias("target"),
        F.lit("url_link").alias("edge_type"),
        F.col("post_uid"),
        F.col("observed_at"),
        F.lit(False).alias("is_artificial_crawl_edge"),
    ).where(F.col("target").isNotNull() & (F.col("target") != ""))
    forward_edges = messages.select(
        F.col("canonical_channel_id").alias("source_channel_id"),
        F.col("post_uid"),
        F.col("published_at").alias("observed_at"),
        F.explode(
            F.array(
                F.struct(F.lit("forwarded_from").alias("edge_type"), F.col("shared_id").alias("target")),
                F.struct(F.lit("quoted_post").alias("edge_type"), F.col("quoted_id").alias("target")),
                F.struct(F.lit("reply_to").alias("edge_type"), F.col("replied_id").alias("target")),
            )
        ).alias("edge"),
    ).where(F.col("edge.target").isNotNull()).select(
        F.sha2(F.concat_ws(":", "source_channel_id", "post_uid", F.col("edge.target"), F.col("edge.edge_type")), 256).alias("edge_id"),
        F.col("source_channel_id"),
        F.col("edge.target").cast("string").alias("target"),
        F.col("edge.edge_type").alias("edge_type"),
        F.col("post_uid"),
        F.col("observed_at"),
        F.lit(False).alias("is_artificial_crawl_edge"),
    )
    edges = _contract_select(url_edges.unionByName(forward_edges, allowMissingColumns=True), "silver_telegram_edges")
    ctx.write("silver_telegram_edges", edges)
    degree = edges.groupBy("edge_type", "source_channel_id").agg(F.count("*").alias("value"))
    window = Window.partitionBy("edge_type").orderBy(F.col("value").desc(), F.col("source_channel_id"))
    summaries = degree.withColumn("rank", F.row_number().over(window)).select(
        F.lit(ctx.config.analysis.run_id).alias("run_id"),
        F.col("edge_type"),
        F.col("source_channel_id").alias("node_id"),
        F.lit("outdegree").alias("statistic"),
        F.col("value").cast("double"),
        F.col("rank"),
        F.lit(None).cast("string").alias("notes"),
    )
    ctx.write("gold_network_summaries", _contract_select(summaries, "gold_network_summaries"), replace_where=f"run_id = {_sql_literal(ctx.config.analysis.run_id)}")
    return {"stage": "11", "status": "network_tables_written"}


def stage_12(ctx: PipelineContext) -> dict[str, Any]:
    network = ctx.target_df("gold_network_summaries")
    random_walk = ctx.target_df("silver_random_walk_exposures")
    rows = []
    for kappa in (1, 10, 30, 100):
        rows.append(
            {
                "run_id": ctx.config.analysis.run_id,
                "check_name": "missed_audience_dark_mass",
                "scenario": f"kappa_{kappa}",
                "metric": "omission_bound_available",
                "baseline_value": 0.0,
                "scenario_value": None if random_walk is None or not _has_rows(random_walk) else float(kappa),
                "delta": None,
                "notes": "Requires random-walk exposures for empirical bounds; organic network summaries are available separately."
                if network is not None
                else "Network summaries missing.",
            }
        )
    df = ctx.spark.createDataFrame(rows, _schema_for_contract(get_contract("gold_robustness_summaries")))
    ctx.write("gold_robustness_summaries", df, replace_where=f"run_id = {_sql_literal(ctx.config.analysis.run_id)} AND check_name = 'missed_audience_dark_mass'")
    return {"stage": "12", "status": "missed_audience_sensitivity_written"}


def stage_13(ctx: PipelineContext) -> dict[str, Any]:
    sample = ctx.target_df("gold_too_sample_frame")
    rows = []
    if sample is not None:
        for threshold in ctx.config.analysis.member_thresholds:
            value = (
                sample.where((F.col("metric_name") == ctx.config.analysis.member_metric) & (F.col("metric_value") >= float(threshold)))
                .agg(F.count("*").alias("n"))
                .first()["n"]
            )
            rows.append(
                {
                    "run_id": ctx.config.analysis.run_id,
                    "check_name": "member_threshold_sensitivity",
                    "scenario": f"threshold_{threshold}",
                    "metric": "selected_channels",
                    "baseline_value": None,
                    "scenario_value": float(value),
                    "delta": None,
                    "notes": "Threshold-only selected-channel count.",
                }
            )
    if not rows:
        rows.append(
            {
                "run_id": ctx.config.analysis.run_id,
                "check_name": "pipeline_inputs",
                "scenario": "missing_sample",
                "metric": "status",
                "baseline_value": None,
                "scenario_value": None,
                "delta": None,
                "notes": "gold_too_sample_frame missing.",
            }
        )
    df = ctx.spark.createDataFrame(rows, _schema_for_contract(get_contract("gold_robustness_summaries")))
    ctx.write("gold_robustness_summaries", df, replace_where=f"run_id = {_sql_literal(ctx.config.analysis.run_id)} AND check_name IN ('member_threshold_sensitivity', 'pipeline_inputs')")
    return {"stage": "13", "status": "robustness_written"}


def stage_14(ctx: PipelineContext) -> dict[str, Any]:
    rows = []
    for name in ctx.config.outputs.planned_tables:
        fqtn = ctx.target(name)
        exists = ctx.source_exists(fqtn)
        row_count = int(ctx.spark.table(fqtn).count()) if exists and ctx.config.analysis.should_scan else None
        rows.append(
            {
                "run_id": ctx.config.analysis.run_id,
                "artifact_name": name,
                "artifact_type": "delta_table",
                "source_table": fqtn,
                "row_count": row_count,
                "created_at_utc": datetime.now(timezone.utc),
                "notes": "exists" if exists else "not_materialized",
            }
        )
    df = ctx.spark.createDataFrame(rows, _schema_for_contract(get_contract("gold_reporting_manifest")))
    ctx.write("gold_reporting_manifest", df, replace_where=f"run_id = {_sql_literal(ctx.config.analysis.run_id)} AND artifact_type = 'delta_table'")
    return {"stage": "14", "status": "reporting_manifest_written"}


STAGE_DISPATCH: dict[str, Callable[[PipelineContext], dict[str, Any]]] = {
    "00": stage_00,
    "01": stage_01,
    "02": stage_02,
    "03": stage_03,
    "04": stage_04,
    "05": stage_05,
    "06": stage_06,
    "06b": stage_06b,
    "07": stage_07,
    "08": stage_08,
    "09": stage_09,
    "10": stage_10,
    "11": stage_11,
    "12": stage_12,
    "13": stage_13,
    "14": stage_14,
}


def run_stage(stage_id: str, spark: SparkSession, config: ProjectConfig) -> dict[str, Any]:
    normalized = stage_id.lower().removeprefix("notebooks/").split("_", 1)[0]
    if normalized == "06b":
        key = "06b"
    else:
        key = normalized[:2]
    if key not in STAGE_DISPATCH:
        raise KeyError(f"Unknown Telegram descriptive stage {stage_id!r}. Known: {sorted(STAGE_DISPATCH)}")
    if not config.analysis.should_scan:
        return {
            "stage_id": key,
            "stage_name": STAGE_NAMES[key],
            "execution_mode": config.analysis.execution_mode,
            "write_outputs": False,
            "status": "manifest_only_no_source_reads_or_writes",
            "source_tables": _source_manifest(config),
            "output_tables": config.outputs.manifest(),
            "output_governance_warnings": config.outputs.governance_warnings(),
        }
    _require_spark()
    ctx = PipelineContext(spark=spark, config=config)
    result = STAGE_DISPATCH[key](ctx)
    result.update(
        {
            "stage_id": key,
            "stage_name": STAGE_NAMES[key],
            "execution_mode": config.analysis.execution_mode,
            "write_outputs": config.analysis.write_outputs,
            "output_tables": config.outputs.manifest(),
        }
    )
    return result
