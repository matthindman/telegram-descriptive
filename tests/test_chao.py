import pytest

from telegram_descriptive.estimation.chao import chao2, chao2_from_counts


def test_chao2_bias_corrected_no_doubletons():
    estimate = chao2([{"a", "b"}, {"b", "c"}, {"b", "d"}])

    assert estimate.samples == 3
    assert estimate.observed_species == 4
    assert estimate.singletons == 3
    assert estimate.doubletons == 0
    assert estimate.estimate == 6


def test_chao2_empty_samples():
    estimate = chao2([])

    assert estimate.samples == 0
    assert estimate.observed_species == 0
    assert estimate.estimate == 0


def test_chao2_from_counts_matches_incidence_formula():
    assert chao2_from_counts(samples=3, observed_species=4, singletons=3, doubletons=0) == 6


def test_chao2_from_counts_validates_count_inputs():
    assert chao2_from_counts(samples=0, observed_species=2, singletons=0, doubletons=0) == 2
    with pytest.raises(ValueError, match="nonnegative"):
        chao2_from_counts(samples=1, observed_species=-1, singletons=0, doubletons=0)
