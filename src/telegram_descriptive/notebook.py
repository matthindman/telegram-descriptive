"""Utilities for thin Databricks notebook orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from telegram_descriptive.config import AnalysisConfig, OutputTables, ProjectConfig, SourceTables


def in_databricks() -> bool:
    return _dbutils() is not None


def _dbutils() -> Any | None:
    """Best-effort access to Databricks dbutils from an imported module."""

    try:
        import builtins

        candidate = getattr(builtins, "dbutils", None)
        if candidate is not None:
            return candidate
    except Exception:
        pass
    try:
        from IPython import get_ipython

        shell = get_ipython()
        if shell is not None:
            candidate = shell.user_ns.get("dbutils")
            if candidate is not None:
                return candidate
    except Exception:
        pass
    try:
        from pyspark.dbutils import DBUtils
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.getOrCreate()
        return DBUtils(spark)
    except Exception:
        return None


def create_text_widget(name: str, default: str, label: str | None = None) -> None:
    utils = _dbutils()
    if utils is None:
        return
    try:
        utils.widgets.text(name, default, label or name)
    except Exception:
        pass


def get_widget(name: str, default: str) -> str:
    utils = _dbutils()
    if utils is not None:
        try:
            value = utils.widgets.get(name)
            return value if value not in (None, "") else default
        except Exception:
            pass
    try:
        import os

        return os.environ.get(name.upper(), default)
    except Exception:
        return default


def get_int_widget(name: str, default: int) -> int:
    raw = get_widget(name, str(default)).strip()
    return int(raw) if raw else default


def get_bool_widget(name: str, default: bool) -> bool:
    return get_widget(name, str(default)).strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def get_int_tuple_widget(name: str, default: tuple[int, ...]) -> tuple[int, ...]:
    raw = get_widget(name, ",".join(str(value) for value in default)).strip()
    if not raw:
        return default
    return tuple(int(value.strip()) for value in raw.split(",") if value.strip())


def create_standard_widgets() -> None:
    """Create the common widget surface used by every Databricks stage."""

    defaults = {
        "source_catalog": "prod_tads",
        "telegram_schema": "telegram",
        "random_walk_schema": "telegram_random_walk",
        "too_schema": "telegram_too",
        "output_catalog": "dev_sean",
        "output_schema": "matt",
        "output_table_prefix": "telegram_descriptive",
        "execution_mode": "manifest_only",
        "run_id": "manual",
        "sample_version": "telegram_too_v1",
        "ranking_version": "telegram_rank_v1",
        "estimate_version": "telegram_estimates_v1",
        "lid_run_id": "telegram_lid_v1",
        "topic_run_id": "telegram_topics_v1",
        "random_seed": "20260602",
        "smoke_limit": "50000",
        "write_outputs": "true",
        "metric_snapshot_policy": "latest",
        "too_member_threshold": "10000",
        "too_top_n": "1662",
        "rank_boundaries": "50,100,200,500,1000",
        "member_thresholds": "1000,10000,100000,1000000",
        "top_n_values": "100,500,1000,1662",
        "export_root": "/Volumes/dev_sean/matt/models/telegram_descriptive",
    }
    for name, default in defaults.items():
        create_text_widget(name, default)


def project_config_from_widgets() -> ProjectConfig:
    source_catalog = get_widget("source_catalog", "prod_tads")
    sources = SourceTables(
        catalog=source_catalog,
        telegram_schema=get_widget("telegram_schema", "telegram"),
        random_walk_schema=get_widget("random_walk_schema", "telegram_random_walk"),
        too_schema=get_widget("too_schema", "telegram_too"),
    )
    outputs = OutputTables(
        catalog=get_widget("output_catalog", "dev_sean"),
        schema=get_widget("output_schema", "matt"),
        prefix=get_widget("output_table_prefix", "telegram_descriptive"),
    )
    analysis = AnalysisConfig(
        execution_mode=get_widget("execution_mode", "manifest_only"),
        run_id=get_widget("run_id", "manual"),
        sample_version=get_widget("sample_version", "telegram_too_v1"),
        ranking_version=get_widget("ranking_version", "telegram_rank_v1"),
        estimate_version=get_widget("estimate_version", "telegram_estimates_v1"),
        lid_run_id=get_widget("lid_run_id", "telegram_lid_v1"),
        topic_run_id=get_widget("topic_run_id", "telegram_topics_v1"),
        random_seed=get_int_widget("random_seed", 20260602),
        smoke_limit=get_int_widget("smoke_limit", 50_000),
        write_outputs=get_bool_widget("write_outputs", True),
        metric_snapshot_policy=get_widget("metric_snapshot_policy", "latest"),
        too_member_threshold=get_int_widget("too_member_threshold", 10_000),
        too_top_n=get_int_widget("too_top_n", 1_662),
        rank_boundaries=get_int_tuple_widget("rank_boundaries", (50, 100, 200, 500, 1000)),
        member_thresholds=get_int_tuple_widget("member_thresholds", (1_000, 10_000, 100_000, 1_000_000)),
        top_n_values=get_int_tuple_widget("top_n_values", (100, 500, 1000, 1662)),
        export_root=get_widget("export_root", "/Volumes/dev_sean/matt/models/telegram_descriptive"),
    )
    return ProjectConfig(sources=sources, outputs=outputs, analysis=analysis)


def stage_manifest(stage: str, config: ProjectConfig, outputs: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "stage": stage,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_mode": config.analysis.execution_mode,
        "sources": config.sources.__dict__,
        "outputs": config.outputs.manifest(),
        "output_governance_warnings": config.outputs.governance_warnings(),
        "stage_outputs": outputs or {},
    }


def print_manifest(manifest: dict[str, Any]) -> None:
    import json

    print(json.dumps(manifest, indent=2, sort_keys=True, default=str))
