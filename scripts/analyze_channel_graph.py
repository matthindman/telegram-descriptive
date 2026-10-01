"""Verify the local graph export and build a directed sparse adjacency matrix.

The primary graph includes all extracted links and non-walkback edge records.
Validation is annotation only. Missing annotation means unknown/not recorded,
not that validation was absent, never performed, or unsuccessful.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.sparse import csr_matrix, save_npz
from scipy.sparse.csgraph import connected_components


def result(root, name):
    record = json.loads((root / "results" / f"{name}.json").read_text())
    if record.get("error") or record["status"]["state"] != "SUCCEEDED":
        raise ValueError(f"Unsuccessful SQL result: {name}")
    return record["rows"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root
    graph = root / "graph"
    edges = pq.read_table(graph / "edges.parquet",
                          read_dictionary=["source_handle", "target_handle",
                                           "exposure_crawl_ids", "edge_record_crawl_ids",
                                           "validation_annotations"]).to_pandas()
    nodes = pd.read_parquet(graph / "nodes.parquet").sort_values("handle").reset_index(drop=True)
    if nodes.handle.isna().any() or nodes.handle.duplicated().any():
        raise ValueError("Node identifiers must be unique and nonmissing")
    index = pd.Index(nodes.handle)
    source = index.get_indexer(edges.source_handle)
    target = index.get_indexer(edges.target_handle)
    if (source < 0).any() or (target < 0).any():
        raise ValueError("Graph edge has an unknown endpoint")
    adjacency = csr_matrix((np.ones(len(edges), dtype=np.uint8), (source, target)),
                           shape=(len(nodes), len(nodes)))
    # Detect duplicate exported rows independently of sparse value accumulation.
    if np.unique(source.astype(np.int64) * len(nodes) + target).size != len(edges):
        raise ValueError("Export contains duplicate source-target pairs")
    if ((edges.exposure_records + edges.nonwalkback_edge_records) <= 0).any():
        raise ValueError("Every edge must have recorded link evidence")
    evidence_columns = ["mention_observations", "url_observations",
                        "text_url_observations", "plaintext_observations"]
    if not (edges[evidence_columns].sum(axis=1) == edges.exposure_records).all():
        raise ValueError("Evidence types do not reconcile to observations")
    if not (edges.observed_visits == edges.exposure_records).all():
        raise ValueError("Expected one source-target record per visit")

    flag_columns = ["recorded_true_flag_observations", "recorded_false_flag_observations",
                    "missing_flag_observations"]
    if not (edges[flag_columns].sum(axis=1) == edges.exposure_records).all():
        raise ValueError("Raw validation flags do not reconcile to exposure records")
    annotations = Counter()
    annotation_totals = {}
    for encoded, multiplicity in edges.validation_annotations.value_counts(sort=False).items():
        decoded = json.loads(encoded)
        annotation_totals[encoded] = sum(int(entry["observations"]) for entry in decoded)
        for entry in decoded:
            key = (entry["validation_status"], entry["validation_reason"],
                   entry["recorded_target_is_valid_public_channel"])
            annotations[key] += int(multiplicity) * int(entry["observations"])
    remote_annotations = {
        (r["validation_status"], r["validation_reason"],
         {"true": True, "false": False, None: None}[r["target_is_valid_public_channel"]]):
        int(r["records"]) for r in result(root, "all_validation_annotations")
    }
    if dict(annotations) != remote_annotations:
        raise ValueError("Raw validation annotation counts differ from independent SQL")
    if not (edges.validation_annotations.map(annotation_totals).to_numpy()
            == edges.exposure_records.to_numpy()).all():
        raise ValueError("Per-pair annotation totals do not reconcile")
    if not ((edges.validation_annotations == "[]") == (edges.exposure_records == 0)).all():
        raise ValueError("Edge-only pairs must retain unavailable exposure annotations")
    if int(edges.exposure_records.sum()) != int(result(root, "all_observation_quality")[0]["records"]):
        raise ValueError("Not all exposure records were retained")
    expected_edge_records = sum(int(row["records"]) for row in result(root, "edge_record_types")
                                if row["walkback"] == "false")
    if int(edges.nonwalkback_edge_records.sum()) != expected_edge_records:
        raise ValueError("Not all non-walkback edge records were retained")
    expected_edge_only = int(result(root, "nonwalkback_edges_without_any_exposure")[0]
                            ["pairs_without_any_exposure"])
    if int((edges.exposure_records == 0).sum()) != expected_edge_only:
        raise ValueError("Edge-only pair count differs from independent SQL")
    masks = {
        "all_observed_links": np.ones(len(edges), dtype=bool),
        "exposures_only_all_validation_states": edges.exposure_records.to_numpy() > 0,
        "crawl9_all_exposures": edges.crawl9_exposure_observations.to_numpy() > 0,
        "exposure_urls_all_validation_states":
            (edges.url_observations + edges.text_url_observations).to_numpy() > 0,
    }
    scenarios = {}
    remote = {row["scenario"]: row for row in result(root, "all_link_graph_scenarios")}
    for name, mask in masks.items():
        summary = {
            "nodes": int(np.union1d(source[mask], target[mask]).size),
            "directed_pairs": int(mask.sum()),
            "sources": int(np.unique(source[mask]).size),
            "targets": int(np.unique(target[mask]).size),
            "self_pairs": int(np.count_nonzero(source[mask] == target[mask])),
        }
        if summary != {key: int(remote[name][key]) for key in summary}:
            raise ValueError(f"Local export disagrees with independent SQL audit: {name}")
        scenarios[name] = summary

    structure = {}
    for connection in ("weak", "strong"):
        count, labels = connected_components(adjacency, directed=True, connection=connection)
        sizes = np.bincount(labels)
        structure[f"{connection}_components"] = int(count)
        structure[f"largest_{connection}_component_nodes"] = int(sizes.max())
    reciprocal = int(adjacency.multiply(adjacency.T).nnz)
    structure["reciprocated_directed_pairs"] = reciprocal
    structure["reciprocated_directed_pair_fraction"] = reciprocal / len(edges)
    nodes.insert(0, "node_id", np.arange(len(nodes)))
    nodes["observed_outdegree"] = np.diff(adjacency.indptr)
    nodes["observed_indegree"] = np.bincount(target, minlength=len(nodes))
    nodes["outgoing_links_observed"] = nodes.observed_outdegree > 0
    nodes.to_parquet(graph / "nodes_indexed.parquet", index=False, compression="zstd")
    save_npz(graph / "adjacency_binary.npz", adjacency)
    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scenarios": scenarios, "structure_of_all_observed_links": structure,
        "node_metadata": {
            "missing_registry_row": int((~nodes.registry_row_recorded).sum()),
            "missing_chat_id": int(nodes.chat_id.isna().sum()),
            "target_only_handles": int((nodes.observed_outdegree == 0).sum()),
            "note": "Missing metadata is unknown/not recorded, not proof of invalidity",
        },
        "record_counts": {
            "exposure_records": int(edges.exposure_records.sum()),
            "nonwalkback_edge_records": int(edges.nonwalkback_edge_records.sum()),
            "pairs_without_exposure_annotations": int((edges.exposure_records == 0).sum()),
            "validated_exposure_subset_pairs": int((edges.recorded_true_flag_observations > 0).sum()),
            "note": "Exposure and edge records may describe the same observations; do not add them as an event count",
        },
        "raw_validation_annotation_counts": [
            {"validation_status": k[0], "validation_reason": k[1],
             "recorded_target_is_valid_public_channel": k[2], "observations": v}
            for k, v in annotations.items()
        ],
        "evidence_observations": {col: int(edges[col].sum()) for col in evidence_columns},
        "observed_time_range": [str(edges.first_observed_at.min()),
                                str(edges.last_observed_at.max())],
        "verification": {
            "all_four_scenarios_match_independent_sql": True,
            "all_raw_validation_annotations_match_independent_sql": True,
            "per_pair_validation_annotations_reconcile": True,
            "all_exposure_and_nonwalkback_records_retained": True,
            "edge_only_pairs_retained_with_unavailable_annotations": True,
            "unique_edge_pairs": True, "all_endpoints_have_unique_node_rows": True,
            "evidence_type_counts_reconcile": True,
            "one_observation_per_pair_per_visit": True,
        },
        "scope": "Union of all link exposures and non-walkback edge records in the latest combined crawl export; no validation filter",
        "limitations": [
            "Missing validation is unknown/not recorded in this export, not evidence that validation was absent, never done, or failed.",
            "False flags and all recorded status/reason values are retained verbatim as annotations, not interpreted as current invalidity.",
            "Outgoing links are observed for only a subset of graph nodes. Zero observed degree is not a true zero.",
            "Most nodes lack stable numeric chat IDs; aliases and username changes are not fully resolved.",
            "URL and mention evidence types are available, but original URLs and message IDs are absent from these exposure records.",
            "Source_type describes the retained candidate record; repeated mentions within a visit are collapsed.",
            "Observation weights count source-target visits, not messages or mentions.",
            "Extraction timestamps do not date publication of the underlying links.",
            "Crawls used different candidate modes and configurations; this is a union over observed periods.",
            "Non-walkback edge-only pairs are retained even when exposure annotations are unavailable; their link subtype may be unknown.",
            "Recorded walkbacks are excluded, and no links are inferred from successive visits or restarts.",
            "Registry metadata are a separate snapshot and do not control graph membership.",
        ],
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
