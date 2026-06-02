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
        random_seed=get_int_widget("random_seed", 20260602),
        metric_snapshot_policy=get_widget("metric_snapshot_policy", "latest"),
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
