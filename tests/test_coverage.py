from telegram_descriptive.estimation.coverage import coverage, top_k_share
from telegram_descriptive.estimation.monotone_survival import enforce_nonincreasing, threshold_survival


def test_coverage_clamps_and_handles_bad_denominators():
    assert coverage(5, 10) == 0.5
    assert coverage(15, 10) == 1.0
    assert coverage(5, 0) is None
    assert coverage(5, None) is None


def test_top_k_share():
    assert top_k_share([10, 5, 5], 1) == 0.5


def test_monotone_projection():
    adjusted = enforce_nonincreasing([10, 8, 9, 3])
    assert adjusted == [10, 8.5, 8.5, 3]
    assert threshold_survival({100: 10, 1000: 8, 10000: 9}) == {100: 10, 1000: 8.5, 10000: 8.5}

