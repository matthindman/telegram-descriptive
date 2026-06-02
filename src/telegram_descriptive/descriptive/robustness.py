"""Robustness matrix helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def robustness_matrix(checks: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for check in checks:
        baseline = check.get("baseline")
        alternative = check.get("alternative")
        delta = None
        if baseline is not None and alternative is not None:
            delta = float(alternative) - float(baseline)
        output.append({**dict(check), "delta": delta})
    return output

