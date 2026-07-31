import pytest

from telegram_descriptive.estimation.chao import (
    chao2,
    chao2_equal_effort,
    chao2_from_counts,
    chao2_from_counts_legacy,
)


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


def test_chao2_from_counts_uses_bias_corrected_doubleton_formula():
    assert chao2_from_counts(samples=5, observed_species=10, singletons=4, doubletons=2) == 11.6


def test_legacy_chao2_variant_remains_available_for_reproducibility():
    assert chao2_from_counts_legacy(
        samples=5,
        observed_species=10,
        singletons=4,
        doubletons=2,
    ) == 13.2


def test_chao2_equal_effort_truncates_without_dropping_below_threshold_effort():
    result = chao2_equal_effort(
        {
            "chain_a": ["a", None, "b", "tail_only"],
            "chain_b": ["a", "c", None],
            "chain_c": [None, "d", "a", "tail_only", "tail_only_2"],
        }
    )

    assert result.common_effort == 3
    assert result.chain_efforts == (("chain_a", 4), ("chain_b", 3), ("chain_c", 5))
    assert result.estimate.samples == 3
    assert result.estimate.observed_species == 4
    assert result.estimate.singletons == 3


def test_chao2_equal_effort_rejects_effort_above_shortest_chain():
    with pytest.raises(ValueError, match="least-exposed"):
        chao2_equal_effort({"a": ["x"], "b": ["x", "y"]}, common_effort=2)


def test_chao2_from_counts_validates_count_inputs():
    assert chao2_from_counts(samples=0, observed_species=2, singletons=0, doubletons=0) == 2
    with pytest.raises(ValueError, match="nonnegative"):
        chao2_from_counts(samples=1, observed_species=-1, singletons=0, doubletons=0)
