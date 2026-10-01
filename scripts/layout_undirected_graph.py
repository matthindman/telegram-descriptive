"""Build a quotient layout for the supplied graph without further filtering.

A Leiden quotient graph provides orientation. A binned adjacency matrix
accounts for every supplied edge without computing million-node coordinates.
Input eligibility policy is recorded in the output; no additional sampling or
exposure-frequency weights are applied.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import time

import igraph as ig
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix, load_npz, save_npz, triu
from scipy.sparse.csgraph import connected_components
from sklearn.metrics import normalized_mutual_info_score


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    out = args.root / "visualization"
    out.mkdir(exist_ok=True)
    old_summary = json.loads((out / "layout_summary.json").read_text()) if (
        out / "layout_summary.json").exists() else {}
    started = time.monotonic()
    filter_path = args.root / "graph_filter.json"
    input_filter = json.loads(filter_path.read_text()) if filter_path.exists() else None
    a = load_npz(args.root / "graph/adjacency_binary.npz")
    u = a.maximum(a.T).tocsr()
    u.setdiag(0)
    u.eliminate_zeros()
    u.sort_indices()
    assert (u != u.T).nnz == 0
    n = u.shape[0]
    edges = triu(u, k=1).tocoo()
    source, target = edges.row, edges.col
    degree = np.diff(u.indptr)
    nc, component = connected_components(u, directed=False)
    component_sizes = np.bincount(component)
    giant = int(component_sizes.argmax())
    save_npz(out / "undirected_adjacency.npz", u)
    print(json.dumps({"stage": "undirected", "nodes": n, "edges": len(source),
                      "components": nc, "degree_one": int((degree == 1).sum())}), flush=True)
    graph = ig.Graph(n=n, edges=np.column_stack((source, target)), directed=False)
    member_path = out / "leiden_membership.npy"
    if not member_path.exists():
        runs = []
        primary = None
        for seed in (20260930, 20260931, 20260932):
            ig.set_random_number_generator(random.Random(seed))
            partition = graph.community_leiden(objective_function="modularity",
                                                resolution=1.0, n_iterations=4)
            member = np.array(partition.membership, dtype=np.int32)
            if primary is None:
                primary = member
                np.save(member_path, primary)
            nmi = float(normalized_mutual_info_score(primary, member))
            row = {"seed": seed, "communities": len(partition),
                   "modularity": float(partition.modularity), "nmi_with_primary": nmi}
            runs.append(row)
            print(json.dumps({"stage": "Leiden", **row}), flush=True)
        (out / "community_sensitivity.json").write_text(json.dumps(runs, indent=2) + "\n")
    membership = np.load(member_path)
    k = int(membership.max()) + 1
    counts = np.bincount(membership, minlength=k)
    csrc, cdst = membership[source], membership[target]
    internal = csrc == cdst
    between = coo_matrix((np.ones(np.count_nonzero(~internal), dtype=np.int64),
                          (np.minimum(csrc[~internal], cdst[~internal]),
                           np.maximum(csrc[~internal], cdst[~internal]))), shape=(k, k)).tocsr()
    between.sum_duplicates()
    ce = between.tocoo()
    pd.DataFrame({"source_community": ce.row, "target_community": ce.col,
                  "undirected_links": ce.data}).to_parquet(out / "community_edges.parquet", index=False)
    internal_counts = np.bincount(csrc[internal], minlength=k)
    assert int(ce.data.sum() + internal_counts.sum()) == len(source)
    nodes = pd.read_parquet(args.root / "graph/nodes_indexed.parquet").sort_values("node_id")
    assert np.array_equal(nodes.node_id, np.arange(n))
    top_ids = np.full(k, -1, dtype=np.int64)
    for idx in np.argsort(degree):
        top_ids[membership[idx]] = idx
    communities = pd.DataFrame({"community": np.arange(k), "nodes": counts,
                                "internal_links": internal_counts,
                                "highest_degree_handle": nodes.handle.iloc[top_ids].to_numpy(),
                                "highest_degree": degree[top_ids]})
    communities.to_parquet(out / "communities.parquet", index=False)
    np.savez_compressed(out / "layout_inputs.npz", component=component, degree=degree,
                        source=source, target=target, membership=membership)
    summary = {"nodes": n, "undirected_edges": len(source), "components": nc,
               "largest_component": giant, "largest_component_nodes": int(component_sizes[giant]),
               "smaller_component_nodes": int(n - component_sizes[giant]),
               "degree_one_nodes": int((degree == 1).sum()), "max_degree": int(degree.max()),
               "coarse_communities": k, "internal_edges": int(internal.sum()),
               "between_community_edges": int((~internal).sum()),
               "igraph_version": ig.__version__, "seed": 20260930,
               "leiden_igraph_version": old_summary.get("leiden_igraph_version",
                    old_summary.get("igraph_version", ig.__version__)),
               "symmetrization": "Boolean union A OR A.T; reciprocal links count once",
               "validation_filter": input_filter,
               "isolates": int((degree == 0).sum()), "edge_sampling": False,
               "edge_weights": "binary undirected adjacency; no revisit-frequency weighting"}
    (out / "layout_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    if args.prepare_only:
        return

    ig.set_random_number_generator(random.Random(20260930))
    cg = ig.Graph(n=k, edges=np.column_stack((ce.row, ce.col)), directed=False)
    # Only giant-component communities participate in the main force layout.
    giant_nodes = np.flatnonzero(component == giant)
    giant_communities = np.unique(membership[giant_nodes])
    coarse_giant = cg.induced_subgraph(giant_communities)
    weight_lookup = {(int(s), int(t)): int(w) for s, t, w in zip(ce.row, ce.col, ce.data)}
    weights = []
    for edge in coarse_giant.es:
        pair = tuple(sorted((int(giant_communities[edge.source]),
                             int(giant_communities[edge.target]))))
        weights.append(np.log1p(weight_lookup[pair]))
    if not (out / "community_layout.npy").exists():
        coarse_xy = np.asarray(coarse_giant.layout_fruchterman_reingold(
            weights=weights, niter=1500, grid="nogrid"), dtype=float)
        coarse_xy -= coarse_xy.mean(axis=0)
        coarse_xy /= max(np.ptp(coarse_xy, axis=0).max(), 1e-8)
        center = np.zeros((k, 2))
        center[giant_communities] = coarse_xy * 100
        np.save(out / "community_layout.npy", center)
    summary["coarse_igraph_version"] = old_summary.get("coarse_igraph_version",
        old_summary.get("igraph_version", ig.__version__))
    coords = np.full((n, 2), np.nan)
    summary["published_view"] = "Leiden quotient map plus exact adjacency density"
    # Disconnected components are arranged in a separate atlas, not assigned
    # visually meaningful distances from the giant component.
    small = np.flatnonzero(component != giant)
    coords[degree == 0] = 0.0
    for comp in np.flatnonzero((np.arange(nc) != giant) & (component_sizes > 1)):
        ids = np.flatnonzero(component == comp)
        sub = graph.induced_subgraph(ids)
        if len(ids) == 2:
            xy = np.array([[-0.5, 0], [0.5, 0]])
        else:
            xy = np.asarray(sub.layout_fruchterman_reingold(niter=100, grid="nogrid"))
        xy -= xy.mean(axis=0)
        xy /= max(np.ptp(xy, axis=0).max(), 1e-8)
        coords[ids] = xy
    assert np.isfinite(coords[small]).all() and len(small) == summary["smaller_component_nodes"]
    pd.DataFrame({"node_id": small, "x": coords[small, 0], "y": coords[small, 1],
                  "component": component[small]}).to_parquet(
                      out / "small_component_positions.parquet", index=False)
    summary["elapsed_seconds"] = time.monotonic() - started
    summary["all_nodes_accounted_for"] = True
    summary["giant_individual_coordinates"] = False
    (out / "layout_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"stage": "complete", "seconds": summary["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
