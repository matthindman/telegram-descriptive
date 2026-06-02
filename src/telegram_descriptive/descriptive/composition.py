"""Content composition helpers."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any


def share_by_category(rows: Iterable[Mapping[str, Any]], category_col: str, weight_col: str | None = None) -> list[dict[str, Any]]:
    totals: Counter[str] = Counter()
    total = 0.0
    for row in rows:
        category = str(row.get(category_col) or "unknown")
        weight = float(row.get(weight_col) or 0.0) if weight_col else 1.0
        totals[category] += weight
        total += weight
    return [
        {"category": category, "value": value, "share": value / total if total else 0.0}
        for category, value in sorted(totals.items())
    ]

