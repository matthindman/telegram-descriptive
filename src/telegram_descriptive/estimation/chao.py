"""Incidence-based Chao lower-bound estimators."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Hashable


@dataclass(frozen=True)
class Chao2Estimate:
    samples: int
    observed_species: int
    singletons: int
    doubletons: int
    estimate: float

    @property
    def unseen_lower_bound(self) -> float:
        return max(0.0, self.estimate - self.observed_species)


def chao2(samples: Iterable[Iterable[Hashable]]) -> Chao2Estimate:
    """Bias-corrected Chao2 incidence lower bound using chains as samples."""

    sample_sets = [set(sample) for sample in samples]
    m = len(sample_sets)
    incidence: Counter[Hashable] = Counter()
    for sample in sample_sets:
        incidence.update(sample)
    observed = len(incidence)
    q1 = sum(count == 1 for count in incidence.values())
    q2 = sum(count == 2 for count in incidence.values())
    if m == 0:
        return Chao2Estimate(0, 0, 0, 0, 0.0)
    if q2 > 0:
        estimate = observed + ((m - 1) / m) * (q1 * q1) / (2 * q2)
    else:
        estimate = observed + ((m - 1) / m) * (q1 * (q1 - 1)) / 2
    return Chao2Estimate(m, observed, q1, q2, float(max(observed, estimate)))

