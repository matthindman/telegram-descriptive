"""I/O adapters with Spark-optional behavior.

The library is importable without Databricks. Notebook code can pass Spark
objects into these helpers when running in Databricks.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TableRef:
    catalog: str
    schema: str
    table: str

    @property
    def fqtn(self) -> str:
        return f"{self.catalog}.{self.schema}.{self.table}"


def spark_table_exists(spark: Any, fqtn: str) -> bool:
    """Return whether a Spark table exists, tolerating older Spark APIs."""

    try:
        return bool(spark.catalog.tableExists(fqtn))
    except Exception:
        try:
            spark.table(fqtn).limit(1)
            return True
        except Exception:
            return False


def read_table_if_exists(spark: Any, fqtn: str) -> Any | None:
    if not spark_table_exists(spark, fqtn):
        return None
    return spark.table(fqtn)


def make_run_manifest(config: Mapping[str, Any], git_sha: str | None = None) -> dict[str, Any]:
    return {
        "git_sha": git_sha,
        "config": dict(config),
    }

