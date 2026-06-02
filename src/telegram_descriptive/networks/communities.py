"""Lightweight graph summaries used before Databricks/GraphFrames runs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any


def degree_summary(edges: Iterable[Mapping[str, Any]]) -> dict[str, Counter[str]]:
    outdegree: Counter[str] = Counter()
    indegree: Counter[str] = Counter()
    for edge in edges:
        source = edge.get("source_channel_id")
        target = edge.get("target")
        if source:
            outdegree[str(source)] += 1
        if target:
            indegree[str(target)] += 1
    return {"outdegree": outdegree, "indegree": indegree}


def top_nodes(counter: Counter[str], n: int = 20) -> list[dict[str, Any]]:
    return [{"node": node, "degree": degree} for node, degree in counter.most_common(n)]

