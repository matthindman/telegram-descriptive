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
    estimate = chao2_from_counts(samples=m, observed_species=observed, singletons=q1, doubletons=q2)
    return Chao2Estimate(m, observed, q1, q2, estimate)


def chao2_from_counts(samples: int, observed_species: int, singletons: int, doubletons: int) -> float:
    """Bias-corrected Chao2 estimate from Spark-computed incidence counts."""

    if samples == 0:
        return 0.0
    if doubletons > 0:
        estimate = observed_species + ((samples - 1) / samples) * (singletons * singletons) / (2 * doubletons)
    else:
        estimate = observed_species + ((samples - 1) / samples) * (singletons * (singletons - 1)) / 2
    return float(max(observed_species, estimate))
