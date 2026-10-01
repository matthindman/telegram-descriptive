"""Run a named batch of read-only audit queries and preserve their provenance.

Uses existing Databricks OAuth credentials and an existing SQL warehouse.
Input is a JSON object mapping query names to SELECT/WITH/SHOW/DESCRIBE SQL.
Writes results locally only; never creates or overwrites workspace tables.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time

from databricks.sdk import WorkspaceClient


def execute(client, warehouse, name, sql, output, timeout=900):
    sql = sql.strip().rstrip(";")
    if not re.match(r"^(SELECT|WITH|SHOW|DESCRIBE)\b", sql, re.I):
        raise ValueError(f"Not a read query: {name}")
    if ";" in sql:
        raise ValueError("Each audit entry must contain exactly one SQL statement")
    if not re.fullmatch(r"[a-z0-9_]+", name):
        raise ValueError(f"Invalid result name: {name}")
    started = datetime.now(timezone.utc).isoformat()
    result = {"name": name, "sql": sql, "started_at": started, "warehouse_id": warehouse}
    try:
        response = client.statement_execution.execute_statement(
            warehouse_id=warehouse, statement=sql, wait_timeout="0s",
        )
        result["statement_id"] = response.statement_id
        deadline = time.monotonic() + timeout
        while response.status.state.value in {"PENDING", "RUNNING"}:
            if time.monotonic() > deadline:
                client.statement_execution.cancel_execution(response.statement_id)
                raise TimeoutError(f"Query exceeded {timeout} seconds")
            time.sleep(2)
            response = client.statement_execution.get_statement(response.statement_id)
        result["status"] = response.status.as_dict()
        if response.status.state.value == "SUCCEEDED":
            result["manifest"] = response.manifest.as_dict()
            if response.manifest.truncated:
                raise RuntimeError("Result was truncated; narrow the aggregation before analysis")
            columns = [column.name for column in response.manifest.schema.columns]
            rows = list(response.result.data_array or []) if response.result else []
            next_index = response.result.next_chunk_index if response.result else None
            while next_index is not None:
                chunk = client.statement_execution.get_statement_result_chunk_n(
                    response.statement_id, next_index,
                )
                rows.extend(chunk.data_array or [])
                next_index = chunk.next_chunk_index
            result["rows"] = [dict(zip(columns, row)) for row in rows]
        else:
            result["error"] = response.status.error.as_dict() if response.status.error else None
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    (output / f"{name}.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(json.dumps({"query": name, "rows": len(result.get("rows", [])),
                      "error": result.get("error"), "statement_id": result.get("statement_id")}),
          flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queries", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--profile", default="matt.hindman@researchaccelerator.org")
    parser.add_argument("--warehouse", default="86100da4e1fe8713")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    queries = json.loads(args.queries.read_text())
    client = WorkspaceClient(profile=args.profile)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda entry: execute(client, args.warehouse, *entry, args.output),
                                queries.items()))
    if any(result.get("error") for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
