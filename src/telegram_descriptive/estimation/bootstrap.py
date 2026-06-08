"""Bootstrap utilities for chain-level uncertainty."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

import numpy as np

T = TypeVar("T")


def bootstrap_samples(items: Sequence[T], replicates: int, seed: int = 0) -> list[list[T]]:
    rng = np.random.default_rng(seed)
    if replicates < 0:
        raise ValueError("replicates must be nonnegative")
    if not items:
        return [[] for _ in range(replicates)]
    return [
        [items[int(idx)] for idx in rng.integers(0, len(items), len(items))]
        for _ in range(replicates)
    ]


def bootstrap_interval(
    items: Sequence[T],
    statistic: Callable[[Sequence[T]], float],
    replicates: int = 1000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1")
    draws = [statistic(sample) for sample in bootstrap_samples(items, replicates, seed)]
    if not draws:
        point = statistic(items)
        return point, point, point
    point = statistic(items)
    lower = float(np.quantile(draws, alpha / 2))
    upper = float(np.quantile(draws, 1 - alpha / 2))
    return float(point), lower, upper
