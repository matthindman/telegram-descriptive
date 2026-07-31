import math

import pytest

from telegram_descriptive.networks.links import domain_from_url, url_edges
from telegram_descriptive.networks.missed_audience import (
    audience_normalized_entry_visibility,
    dark_audience_bound,
    darkness_multiplier_for_probability,
    omission_probability_bound,
)


def test_domain_from_url_strips_www_userinfo_and_port():
    assert domain_from_url("https://user:pass@www.Example.com:443/path") == "example.com"


def test_url_edges_skip_rows_without_valid_domain_or_source():
    edges = url_edges(
        [
            {"canonical_channel_id": "c1", "post_uid": "p1", "urls": ["www.example.com/path"]},
            {"canonical_channel_id": "c2", "post_uid": "p2", "urls": ["not a valid host"]},
            {"canonical_channel_id": None, "post_uid": "p3", "urls": ["example.org"]},
        ]
    )

    assert len(edges) == 1
    assert edges[0]["target"] == "example.com"


def test_dark_audience_bound_rejects_negative_inputs():
    with pytest.raises(ValueError, match="observed_cluster_mass"):
        dark_audience_bound(-1, 0.1, 10)


def test_audience_normalized_entry_visibility_uses_audience_share():
    assert audience_normalized_entry_visibility(4, basin_audience=20, total_audience=100) == 20


def test_omission_probability_bound_weakens_as_allowed_darkness_increases():
    assert omission_probability_bound(0.01, 100, 1) == pytest.approx(math.exp(-1))
    assert omission_probability_bound(0.01, 100, 10) == pytest.approx(math.exp(-0.1))
    assert omission_probability_bound(0.01, 100, float("inf")) == 1


def test_omission_probability_bound_rejects_multiplier_below_one():
    with pytest.raises(ValueError, match="at least one"):
        omission_probability_bound(0.01, 100, 0.5)


def test_darkness_multiplier_inverts_omission_bound():
    kappa = darkness_multiplier_for_probability(0.02, 250, 0.05)
    assert omission_probability_bound(0.02, 250, kappa) == pytest.approx(0.05)


def test_darkness_multiplier_rejects_impossible_zero_signal_target():
    with pytest.raises(ValueError, match="visibility signal is zero"):
        darkness_multiplier_for_probability(0, 250, 0.05)
