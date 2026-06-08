"""Missed-audience sensitivity helpers."""

from __future__ import annotations


def dark_audience_bound(observed_cluster_mass: float, entry_intensity: float, kappa: float) -> float:
    """Simple omission bound used for sensitivity tables.

    ``kappa`` is the assumed outside/inside audience multiplier. Infinite kappa
    is represented by ``float("inf")``.
    """

    if observed_cluster_mass < 0:
        raise ValueError("observed_cluster_mass must be nonnegative")
    if entry_intensity < 0:
        raise ValueError("entry_intensity must be nonnegative")
    if kappa == float("inf"):
        return float("inf") if entry_intensity > 0 else 0.0
    if kappa < 0:
        raise ValueError("kappa must be nonnegative")
    return float(observed_cluster_mass) * float(entry_intensity) * float(kappa)
