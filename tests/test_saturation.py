from telegram_descriptive.estimation.saturation import fit_simple_saturation


def test_saturation_fit_returns_boundary_flags_tuple():
    fit = fit_simple_saturation([1, 2, 3], [1, 2, 3])

    assert isinstance(fit.flags, tuple)
    assert fit.asymptote >= fit.observed_final

