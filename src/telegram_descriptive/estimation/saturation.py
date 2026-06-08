"""Saturation curve helpers for discovery increments."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SaturationFit:
    model: str
    observed_final: float
    asymptote: float
    rate: float
    rss: float
    flags: tuple[str, ...] = ()


def fit_simple_saturation(exposures: Sequence[float], discoveries: Sequence[float]) -> SaturationFit:
    """Fit y = A * (1 - exp(-k x)) by grid search.

    This intentionally avoids scipy so local tests can run in a lightweight env.
    """

    x = np.asarray(exposures, dtype=float)
    y = np.asarray(discoveries, dtype=float)
    if len(x) != len(y):
        raise ValueError("exposures and discoveries must have the same length")
    finite_mask = np.isfinite(x) & np.isfinite(y)
    dropped_nonfinite = int(len(x) - finite_mask.sum())
    x = x[finite_mask]
    y = y[finite_mask]
    if len(x) == 0:
        return SaturationFit("simple_exponential", 0.0, 0.0, 0.0, 0.0, ("no_finite_points",))
    if np.any(x < 0) or np.any(y < 0):
        raise ValueError("exposures and discoveries must be nonnegative")
    observed_final = float(np.nanmax(y))
    max_x = float(np.nanmax(x)) if np.nanmax(x) > 0 else 1.0
    best: SaturationFit | None = None
    asymptote_min = max(observed_final, 1.0)
    asymptote_max = max(observed_final * 10, observed_final + 100)
    asymptotes = np.linspace(asymptote_min, asymptote_max, 120)
    rates = np.logspace(-4, 1, 120) / max_x
    for asymptote in asymptotes:
        for rate in rates:
            pred = asymptote * (1 - np.exp(-rate * x))
            rss = float(np.nansum((y - pred) ** 2))
            candidate = SaturationFit("simple_exponential", observed_final, float(asymptote), float(rate), rss)
            if best is None or candidate.rss < best.rss:
                best = candidate
    assert best is not None
    flags: list[str] = []
    if dropped_nonfinite:
        flags.append("dropped_nonfinite_points")
    if np.isclose(best.asymptote, asymptote_max):
        flags.append("asymptote_grid_boundary")
    if np.isclose(best.rate, rates[0]) or np.isclose(best.rate, rates[-1]):
        flags.append("rate_grid_boundary")
    return SaturationFit(best.model, best.observed_final, best.asymptote, best.rate, best.rss, tuple(flags))
