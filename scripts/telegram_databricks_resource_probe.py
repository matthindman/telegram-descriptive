from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from databricks.connect import DatabricksSession
from databricks.sdk.core import Config
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    BooleanType,
    DateType,
    DecimalType,
    DoubleType,
    FloatType,
    IntegerType,
    LongType,
    MapType,
    ShortType,
    StringType,
    StructType,
    TimestampType,
)


PROFILE = os.getenv("DATABRICKS_CONFIG_PROFILE", "hindman.gmail.com@auth.researchaccelerator.org")
CLUSTER_ID = os.getenv("DATABRICKS_CLUSTER_ID", "0303-193859-1ff54asc")
CATALOG = os.getenv("TELEGRAM_CATALOG", "prod_tads")
SCHEMAS = [s.strip() for s in os.getenv("TELEGRAM_SCHEMAS", "telegram,telegram_random_walk,telegram_too").split(",")]
OUT = Path(os.getenv("TELEGRAM_PROBE_OUT", "/tmp/telegram_databricks_resource_probe.json"))
MAX_STRING_VALUE_COUNTS = int(os.getenv("TELEGRAM_PROBE_MAX_STRING_VALUE_COUNTS", "8"))
MAX_COLUMNS_FOR_PROFILE = int(os.getenv("TELEGRAM_PROBE_MAX_COLUMNS_FOR_PROFILE", "28"))
RUN_LIGHT_STATS = os.getenv("TELEGRAM_PROBE_RUN_LIGHT_STATS", "0") == "1"


ID_HINTS = ("id", "username", "handle", "channel", "chat", "message", "post", "run", "chain", "step", "edge", "url")
TIME_HINTS = ("time", "date", "timestamp", "created", "updated", "collected", "capture", "ingest", "last", "first")
METRIC_HINTS = (
    "member",
    "subscriber",
    "view",
    "reaction",
    "reply",
    "forward",
    "count",
    "rank",
    "score",
    "degree",
    "n_",
    "num",
)
TEXT_HINTS = ("title", "about", "description", "bio", "text", "message", "caption", "name")
STATUS_HINTS = ("status", "state", "type", "reason", "eligible", "valid", "public", "private", "deleted", "error")


def dtype_name(dtype: Any) -> str:
    return dtype.simpleString() if hasattr(dtype, "simpleString") else str(dtype)


def is_numeric(dtype: Any) -> bool:
    return isinstance(dtype, (IntegerType, LongType, ShortType, FloatType, DoubleType, DecimalType))


def is_temporal(dtype: Any) -> bool:
    return isinstance(dtype, (TimestampType, DateType))


def is_low_cardinality_candidate(name: str, dtype: Any) -> bool:
    lname = name.lower()
    return isinstance(dtype, (StringType, BooleanType)) and any(h in lname for h in STATUS_HINTS)


def column_role(name: str, dtype: Any) -> str:
    lname = name.lower()
    if any(h in lname for h in ID_HINTS):
        return "identifier/provenance"
    if is_temporal(dtype) or any(h in lname for h in TIME_HINTS):
        return "time"
    if is_numeric(dtype) or any(h in lname for h in METRIC_HINTS):
        return "metric"
    if any(h in lname for h in TEXT_HINTS):
        return "text/metadata"
    if any(h in lname for h in STATUS_HINTS):
        return "status/eligibility"
    if isinstance(dtype, (ArrayType, MapType, StructType)):
        return "nested"
    return "other"


def safe_table_name(fqtn: str) -> str:
    return ".".join(f"`{part}`" for part in fqtn.split("."))


def collect_one(sql: str) -> dict[str, Any]:
    rows = spark.sql(sql).limit(1).collect()
    return rows[0].asDict(recursive=True) if rows else {}


def profile_table(fqtn: str, table_meta: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"name": fqtn, "metadata": table_meta}
    try:
        df = spark.table(fqtn)
    except Exception as exc:
        out["read_error"] = str(exc)[:500]
        return out

    fields = df.schema.fields
    out["columns"] = [
        {
            "name": f.name,
            "type": dtype_name(f.dataType),
            "nullable": f.nullable,
            "role_hint": column_role(f.name, f.dataType),
        }
        for f in fields
    ]

    table_type = str(table_meta.get("table_type") or "").upper()
    if table_type in {"VIEW", "MATERIALIZED_VIEW", "FOREIGN"}:
        out["detail_note"] = f"Skipped DESCRIBE DETAIL for {table_type.lower()}."
    else:
        try:
            detail = collect_one(f"DESCRIBE DETAIL {safe_table_name(fqtn)}")
            keep = [
                "format",
                "id",
                "name",
                "description",
                "location",
                "createdAt",
                "lastModified",
                "partitionColumns",
                "numFiles",
                "sizeInBytes",
            ]
            out["detail"] = {k: str(detail.get(k)) for k in keep if k in detail and detail.get(k) is not None}
        except Exception as exc:
            out["detail_error"] = str(exc)[:500]

    if RUN_LIGHT_STATS:
        try:
            out["row_count"] = int(df.count())
        except Exception as exc:
            out["row_count_error"] = str(exc)[:500]

        candidate_fields = fields[:MAX_COLUMNS_FOR_PROFILE]
        aggs = []
        for f in candidate_fields:
            c = F.col(f.name)
            aggs.append(F.count(c).alias(f"{f.name}__non_null"))
            if is_numeric(f.dataType):
                aggs.extend(
                    [
                        F.min(c).alias(f"{f.name}__min"),
                        F.expr(f"percentile_approx(`{f.name}`, 0.5)").alias(f"{f.name}__median"),
                        F.max(c).alias(f"{f.name}__max"),
                    ]
                )
            elif is_temporal(f.dataType):
                aggs.extend([F.min(c).alias(f"{f.name}__min"), F.max(c).alias(f"{f.name}__max")])
        try:
            summary = df.agg(*aggs).collect()[0].asDict(recursive=True) if aggs else {}
            column_profiles = []
            for f in candidate_fields:
                prof: dict[str, Any] = {"name": f.name}
                prefix = f"{f.name}__"
                for k, v in summary.items():
                    if k.startswith(prefix):
                        prof[k[len(prefix) :]] = str(v) if v is not None else None
                column_profiles.append(prof)
            out["column_profiles"] = column_profiles
        except Exception as exc:
            out["profile_error"] = str(exc)[:500]

        value_counts: dict[str, list[dict[str, Any]]] = {}
        for f in fields:
            if not is_low_cardinality_candidate(f.name, f.dataType):
                continue
            if len(value_counts) >= MAX_STRING_VALUE_COUNTS:
                break
            try:
                rows = (
                    df.groupBy(F.col(f.name).alias("value"))
                    .count()
                    .orderBy(F.desc("count"))
                    .limit(12)
                    .collect()
                )
                value_counts[f.name] = [{"value": str(r["value"]), "count": int(r["count"])} for r in rows]
            except Exception as exc:
                value_counts[f.name] = [{"error": str(exc)[:300]}]
        out["value_counts"] = value_counts
    else:
        out["stats_note"] = "Skipped table scans. Set TELEGRAM_PROBE_RUN_LIGHT_STATS=1 for counts/profiles."

    return out


config = Config(profile=PROFILE, cluster_id=CLUSTER_ID)
spark = DatabricksSession.builder.sdkConfig(config).getOrCreate()

table_info: dict[tuple[str, str], dict[str, Any]] = {}
info_rows = spark.sql(
    f"""
    SELECT table_schema, table_name, table_type, created, last_altered, comment
    FROM `{CATALOG}`.information_schema.tables
    WHERE table_schema IN ({",".join(repr(s) for s in SCHEMAS)})
    """
).collect()
for row in info_rows:
    d = row.asDict(recursive=True)
    table_info[(d["table_schema"], d["table_name"])] = {
        "table_type": d.get("table_type"),
        "created": str(d.get("created")) if d.get("created") is not None else None,
        "last_altered": str(d.get("last_altered")) if d.get("last_altered") is not None else None,
        "comment": d.get("comment"),
    }

result: dict[str, Any] = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "profile": PROFILE,
    "cluster_id": CLUSTER_ID,
    "catalog": CATALOG,
    "schemas": SCHEMAS,
    "run_light_stats": RUN_LIGHT_STATS,
    "tables": [],
}

for schema in SCHEMAS:
    table_rows = spark.sql(f"SHOW TABLES IN `{CATALOG}`.`{schema}`").collect()
    for row in table_rows:
        row_dict = row.asDict(recursive=True)
        table_name = row_dict.get("tableName") or row_dict.get("tableName".lower())
        if not table_name:
            continue
        row_dict.update({k: v for k, v in table_info.get((schema, table_name), {}).items() if v is not None})
        fqtn = f"{CATALOG}.{schema}.{table_name}"
        result["tables"].append(profile_table(fqtn, row_dict))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
print(f"Wrote {OUT}")
print(f"Tables profiled: {len(result['tables'])}")
