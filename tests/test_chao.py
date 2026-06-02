from telegram_descriptive.estimation.chao import chao2


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

