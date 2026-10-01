"""Export audited channel graph SELECT queries to local Parquet files.

Uses the existing SQL warehouse and OAuth profile. No remote data are changed.
Databricks Arrow result chunks avoid the inline-result size limit. Signed download
URLs are used transiently and are never saved in the provenance record.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import Disposition, Format
import pyarrow.ipc as ipc
import pyarrow.parquet as pq
import requests


def export_query(client, warehouse, query_path, output_path, timeout=900, workers=3):
    sql = query_path.read_text().strip()
    if not re.match(r"^(SELECT|WITH)\b", sql, re.I) or ";" in sql:
        raise ValueError("Expected one audited SELECT/WITH query")
    if output_path.exists():
        raise FileExistsError(output_path)
    record_path = output_path.with_suffix(".provenance.json")
    partial = output_path.with_suffix(".partial.parquet")
    record = {"sql": sql, "warehouse_id": warehouse,
              "started_at": datetime.now(timezone.utc).isoformat(),
              "query_file": str(query_path), "output_file": str(output_path)}
    writer = None
    try:
        response = client.statement_execution.execute_statement(
            statement=sql, warehouse_id=warehouse, wait_timeout="0s",
            disposition=Disposition.EXTERNAL_LINKS, format=Format.ARROW_STREAM,
        )
        record["statement_id"] = response.statement_id
        deadline = time.monotonic() + timeout
        while response.status.state.value in {"PENDING", "RUNNING"}:
            if time.monotonic() > deadline:
                client.statement_execution.cancel_execution(response.statement_id)
                raise TimeoutError("SQL export exceeded timeout")
            time.sleep(2)
            response = client.statement_execution.get_statement(response.statement_id)
        record["status"] = response.status.as_dict()
        if response.status.state.value != "SUCCEEDED":
            raise RuntimeError(f"SQL export failed: {response.status.error}")
        manifest = response.manifest
        record["manifest"] = manifest.as_dict()
        if manifest.truncated:
            raise RuntimeError("Refusing truncated result")
        observed_rows = 0
        chunks = []

        def fetch_chunk(chunk_index):
            chunk = (response.result if chunk_index == 0 else
                     client.statement_execution.get_statement_result_chunk_n(
                         response.statement_id, chunk_index))
            links = chunk.external_links or []
            if len(links) != 1 or links[0].chunk_index != chunk_index:
                raise RuntimeError("Unexpected external chunk structure")
            link = links[0]
            # Do not include download URLs (temporary credentials) in errors.
            with tempfile.TemporaryFile() as arrow_file:
                try:
                    with requests.get(link.external_link, headers=link.http_headers or {},
                                      stream=True, timeout=(30, 120)) as download:
                        if download.status_code != 200:
                            raise RuntimeError(f"Result download HTTP {download.status_code}")
                        for block in download.iter_content(1024 * 1024):
                            arrow_file.write(block)
                except requests.RequestException as exc:
                    raise RuntimeError(f"Result download failed ({type(exc).__name__})") from None
                arrow_file.seek(0)
                with ipc.open_stream(arrow_file) as stream:
                    table = stream.read_all()
            if table.num_rows != link.row_count:
                raise RuntimeError("Downloaded chunk row count differs from manifest")
            return chunk_index, table

        # Fetch bounded groups concurrently; write in chunk order with one writer.
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for start in range(0, manifest.total_chunk_count, workers):
                indices = range(start, min(start + workers, manifest.total_chunk_count))
                for chunk_index, table in pool.map(fetch_chunk, indices):
                    if writer is None:
                        writer = pq.ParquetWriter(partial, table.schema, compression="zstd")
                    writer.write_table(table)
                    observed_rows += table.num_rows
                    chunks.append({"chunk_index": chunk_index, "rows": table.num_rows})
                    print(json.dumps({"file": output_path.name, "chunk": chunk_index,
                                      "downloaded_rows": observed_rows}), flush=True)
        if observed_rows != manifest.total_row_count:
            raise RuntimeError("Export row count differs from manifest")
        if writer is None:
            raise RuntimeError("Expected a nonempty graph export")
        writer.close()
        writer = None
        if pq.ParquetFile(partial).metadata.num_rows != observed_rows:
            raise RuntimeError("Parquet row count differs from downloaded rows")
        partial.replace(output_path)
        record["downloaded_rows"] = observed_rows
        record["downloaded_chunks"] = chunks
        record["bytes"] = output_path.stat().st_size
        digest = hashlib.sha256()
        with output_path.open("rb") as exported:
            for block in iter(lambda: exported.read(1024 * 1024), b""):
                digest.update(block)
        record["sha256"] = digest.hexdigest()
        record["verified_complete"] = True
    except Exception as exc:
        record["error"] = str(exc)
        raise
    finally:
        if writer is not None:
            writer.close()
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        record_path.write_text(json.dumps(record, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--profile", default="matt.hindman@researchaccelerator.org")
    parser.add_argument("--warehouse", default="86100da4e1fe8713")
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=3)
    args = parser.parse_args()
    output = args.root / "graph"
    output.mkdir(parents=True, exist_ok=True)
    client = WorkspaceClient(profile=args.profile)
    for kind in ("edges", "nodes"):
        export_query(client, args.warehouse, args.root / "queries" / f"export_{kind}.sql",
                     output / f"{kind}.parquet", workers=args.workers)


if __name__ == "__main__":
    main()
