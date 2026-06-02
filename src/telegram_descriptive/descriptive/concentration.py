"""Concentration metrics for audience and engagement."""

from __future__ import annotations

from collections.abc import Sequence


def gini(values: Sequence[float]) -> float:
    clean = sorted(float(v) for v in values if v is not None and float(v) >= 0)
    n = len(clean)
    if n == 0:
        return 0.0
    total = sum(clean)
    if total == 0:
        return 0.0
    weighted_sum = sum((idx + 1) * value for idx, value in enumerate(clean))
    return (2 * weighted_sum) / (n * total) - (n + 1) / n


def hhi(values: Sequence[float]) -> float:
    clean = [float(v) for v in values if v is not None and float(v) >= 0]
    total = sum(clean)
    if total == 0:
        return 0.0
    return sum((value / total) ** 2 for value in clean)


def concentration_ratio(values: Sequence[float], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    clean = sorted((float(v) for v in values if v is not None and float(v) >= 0), reverse=True)
    total = sum(clean)
    if total == 0:
        return 0.0
    return sum(clean[:k]) / total

