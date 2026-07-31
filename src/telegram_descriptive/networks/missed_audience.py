"""Missed-audience sensitivity helpers."""

from __future__ import annotations

import math


def audience_normalized_entry_visibility(
    entry_intensity: float,
    basin_audience: float,
    total_audience: float,
) -> float:
    """Independent entry opportunities per unit of observed audience share."""

    if entry_intensity < 0:
        raise ValueError("entry_intensity must be nonnegative")
    if basin_audience <= 0:
        raise ValueError("basin_audience must be positive")
    if total_audience <= 0:
        raise ValueError("total_audience must be positive")
    if basin_audience > total_audience:
        raise ValueError("basin_audience cannot exceed total_audience")
    return float(entry_intensity) / (float(basin_audience) / float(total_audience))


def omission_probability_bound(
    audience_share: float,
    entry_visibility: float,
    kappa: float,
) -> float:
    """Upper bound on complete omission under the documented darkness model.

    ``kappa`` is how many times less visible per unit audience a hypothetical
    unseen basin may be than the observed lower-tail benchmark. ``inf`` is the
    assumption-free case and therefore yields no finite protection (bound 1).
    """

    if not 0 <= audience_share <= 1:
        raise ValueError("audience_share must be between zero and one")
    if math.isnan(entry_visibility) or entry_visibility < 0:
        raise ValueError("entry_visibility must be nonnegative and not NaN")
    if math.isnan(kappa) or kappa < 1:
        raise ValueError("kappa must be at least one")
    if math.isinf(kappa):
        return 1.0
    signal = float(entry_visibility) * float(audience_share)
    return float(math.exp(-signal / float(kappa)))


def darkness_multiplier_for_probability(
    audience_share: float,
    entry_visibility: float,
    omission_probability: float,
) -> float:
    """Solve for the darkness multiplier corresponding to an omission bound.

    Values below one mean that even a basin as visible as the observed
    benchmark (``kappa=1``) cannot attain the requested probability bound.
    """

    if not 0 <= audience_share <= 1:
        raise ValueError("audience_share must be between zero and one")
    if math.isnan(entry_visibility) or entry_visibility < 0:
        raise ValueError("entry_visibility must be nonnegative and not NaN")
    if not 0 < omission_probability <= 1:
        raise ValueError("omission_probability must be in (0, 1]")
    signal = float(entry_visibility) * float(audience_share)
    if omission_probability == 1:
        return float("inf")
    if signal == 0:
        raise ValueError("no finite darkness multiplier exists when the visibility signal is zero")
    return float(-signal / math.log(float(omission_probability)))


def dark_audience_bound(observed_cluster_mass: float, entry_intensity: float, kappa: float) -> float:
    """Backward-compatible name for the complete-omission probability bound.

    ``observed_cluster_mass`` is interpreted as audience share (delta) and
    ``entry_intensity`` as the audience-normalized lower-tail visibility
    benchmark. New code should call :func:`omission_probability_bound`.
    """

    if observed_cluster_mass < 0:
        raise ValueError("observed_cluster_mass must be nonnegative")
    return omission_probability_bound(observed_cluster_mass, entry_intensity, kappa)
