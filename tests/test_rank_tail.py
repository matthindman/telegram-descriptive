import math

from telegram_descriptive.estimation.rank_tail import continuous_tail_mass, estimate_tail_ladder, fit_tail_parameters


def test_fit_tail_parameters_recovers_power_law_slope():
    values = [10000 / (rank**1.4) for rank in range(1, 501)]
    params = fit_tail_parameters(values, boundary_rank=100, fitting_window=80)

    assert params.boundary_rank == 100
    assert math.isclose(params.alpha0, 1.4, rel_tol=0.05)
    assert params.y0 > 0
    assert "alpha_lte_one" not in params.flags


def test_tail_ladder_returns_ordered_models():
    boundary = 100
    values = [
        5000
        * math.exp(
            -1.2 * math.log(rank / boundary)
            - 0.2 * math.log(rank / boundary) ** 2 / 2
            - 0.12 * math.log(rank / boundary) ** 3 / 6
            - 0.06 * math.log(rank / boundary) ** 4 / 24
        )
        for rank in range(1, 1000)
    ]
    estimates = estimate_tail_ladder(values, boundary_rank=100, fitting_window=80)

    assert [estimate.model for estimate in estimates] == ["D0", "D1", "D2", "D3"]
    assert all(estimate.total_mass >= sum(values[:100]) for estimate in estimates)
    assert estimates[0].tail_mass > estimates[1].tail_mass > estimates[2].tail_mass > estimates[3].tail_mass


def test_unbounded_tail_is_flagged_for_alpha_lte_one_without_steepening():
    values = [10000 / (rank**0.8) for rank in range(1, 500)]
    params = fit_tail_parameters(values, boundary_rank=100, fitting_window=80)

    tail, flags = continuous_tail_mass(params, "D2")

    assert math.isinf(tail)
    assert "infinite_d2_tail" in flags
    assert "d2_degenerate_to_d1" in flags
