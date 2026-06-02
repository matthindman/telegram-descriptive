"""Convergence diagnostics for crawl discovery curves."""

from __future__ import annotations

from collections.abc import Sequence


def rolling_discovery_rate(cumulative_discoveries: Sequence[float], window: int) -> list[float]:
    """Compute discovery increments per exposure over a rolling window."""

    if window <= 0:
        raise ValueError("window must be positive")
    values = [float(v) for v in cumulative_discoveries]
    rates: list[float] = []
    for idx, value in enumerate(values):
        if idx < window:
            rates.append(value / (idx + 1))
        else:
            rates.append((value - values[idx - window]) / window)
    return rates


def first_stable_index(rates: Sequence[float], tolerance: float, min_run: int) -> int | None:
    """Return first index where rates stay within tolerance for min_run points."""

    if min_run <= 0:
        raise ValueError("min_run must be positive")
    values = [float(v) for v in rates]
    for idx in range(0, max(0, len(values) - min_run + 1)):
        window = values[idx : idx + min_run]
        if max(window) - min(window) <= tolerance:
            return idx
    return None

