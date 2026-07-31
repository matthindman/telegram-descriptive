"""Incidence-based Chao lower-bound estimators."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
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


@dataclass(frozen=True)
class EqualEffortChao2Estimate:
    """Chao2 result after truncating every chain to a common exposure effort."""

    common_effort: int
    chain_efforts: tuple[tuple[Hashable, int], ...]
    estimate: Chao2Estimate


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
    """Documented bias-corrected Chao2 estimate from incidence counts.

    This project uses the finite-sample correction from the registered method:
    ``D + ((m - 1) / m) * Q1 * (Q1 - 1) / (2 * (Q2 + 1))``.
    """

    if min(samples, observed_species, singletons, doubletons) < 0:
        raise ValueError("Chao2 counts must be nonnegative")
    if samples == 0:
        return float(observed_species)
    estimate = observed_species + ((samples - 1) / samples) * (
        singletons * (singletons - 1)
    ) / (2 * (doubletons + 1))
    return float(max(observed_species, estimate))


def chao2_from_counts_legacy(
    samples: int,
    observed_species: int,
    singletons: int,
    doubletons: int,
) -> float:
    """Pre-spec Chao2 variant retained only for reproducing older outputs.

    When doubletons are present this uses ``Q1**2 / (2 * Q2)``. New analysis
    must use :func:`chao2_from_counts`, which implements the registered
    bias-corrected estimator.
    """

    if min(samples, observed_species, singletons, doubletons) < 0:
        raise ValueError("Chao2 counts must be nonnegative")
    if samples == 0:
        return float(observed_species)
    if doubletons > 0:
        unseen = (singletons * singletons) / (2 * doubletons)
    else:
        unseen = singletons * (singletons - 1) / 2
    estimate = observed_species + ((samples - 1) / samples) * unseen
    return float(max(observed_species, estimate))


def chao2_equal_effort(
    chains: Mapping[Hashable, Sequence[Hashable | None]],
    common_effort: int | None = None,
) -> EqualEffortChao2Estimate:
    """Compute Chao2 after equalizing independent chains by exposure count.

    Each sequence position is one eligible exposure opportunity. Use ``None``
    for an exposure whose target is outside the subscriber threshold being
    estimated; it still counts toward effort but not toward incidence.
    """

    efforts = tuple((chain_id, len(sequence)) for chain_id, sequence in chains.items())
    maximum_common_effort = min((effort for _, effort in efforts), default=0)
    if common_effort is None:
        common_effort = maximum_common_effort
    if common_effort < 0:
        raise ValueError("common_effort must be nonnegative")
    if common_effort > maximum_common_effort:
        raise ValueError("common_effort cannot exceed the least-exposed chain")

    equalized = [
        [target for target in sequence[:common_effort] if target is not None]
        for sequence in chains.values()
    ]
    return EqualEffortChao2Estimate(
        common_effort=common_effort,
        chain_efforts=efforts,
        estimate=chao2(equalized),
    )
