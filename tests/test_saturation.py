import math

import pytest

from telegram_descriptive.estimation.saturation import fit_simple_saturation


def test_saturation_fit_returns_boundary_flags_tuple():
    fit = fit_simple_saturation([1, 2, 3], [1, 2, 3])

    assert isinstance(fit.flags, tuple)
    assert fit.asymptote >= fit.observed_final


def test_saturation_fit_drops_nonfinite_pairs_and_rejects_negative_counts():
    fit = fit_simple_saturation([1, math.nan, 3], [1, 2, 3])

    assert "dropped_nonfinite_points" in fit.flags
    with pytest.raises(ValueError, match="nonnegative"):
        fit_simple_saturation([1, -2], [1, 2])
