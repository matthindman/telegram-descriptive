"""Research table formatting helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def methods_table(estimates: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in estimates:
        output.append(
            {
                "estimand": row.get("estimand"),
                "metric": row.get("metric_name"),
                "threshold": row.get("threshold"),
                "model": row.get("model"),
                "observed": row.get("observed_n"),
                "estimate": row.get("estimate"),
                "interval": (
                    f"{row.get('lower_ci')}-{row.get('upper_ci')}"
                    if row.get("lower_ci") is not None and row.get("upper_ci") is not None
                    else None
                ),
                "flags": ", ".join(row.get("diagnostic_flags") or []),
            }
        )
    return output

