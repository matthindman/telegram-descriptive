import pytest

from telegram_descriptive.networks.links import domain_from_url, url_edges
from telegram_descriptive.networks.missed_audience import dark_audience_bound


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
