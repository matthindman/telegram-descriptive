import pytest

from telegram_descriptive.crawl.exposure import (
    collapse_duplicate_exposures,
    source_visit_exposure_id,
)


def test_collapse_duplicate_exposures_only_collapses_within_batch():
    rows = [
        {
            "crawl_run_id": "run",
            "chain_id": "chain_a",
            "batch_id": "visit_1",
            "target_channel_id": "target",
        },
        {
            "crawl_run_id": "run",
            "chain_id": "chain_a",
            "batch_id": "visit_1",
            "target_channel_id": "target",
        },
        {
            "crawl_run_id": "run",
            "chain_id": "chain_a",
            "batch_id": "visit_2",
            "target_channel_id": "target",
        },
        {
            "crawl_run_id": "run",
            "chain_id": "chain_b",
            "batch_id": "visit_3",
            "target_channel_id": "target",
        },
    ]

    collapsed = collapse_duplicate_exposures(rows)

    assert len(collapsed) == 3
    assert [row["duplicate_exposure_count"] for row in collapsed] == [2, 1, 1]


def test_collapse_duplicate_exposures_rejects_missing_visit_key():
    with pytest.raises(ValueError, match="batch_id"):
        collapse_duplicate_exposures(
            [{"crawl_run_id": "run", "target_channel_id": "target"}]
        )


def test_source_visit_exposure_id_is_stable_and_visit_specific():
    assert source_visit_exposure_id("run", "visit_1", "target") == source_visit_exposure_id(
        "run", "visit_1", "target"
    )
    assert source_visit_exposure_id("run", "visit_1", "target") != source_visit_exposure_id(
        "run", "visit_2", "target"
    )


def test_source_visit_exposure_id_rejects_incomplete_keys():
    with pytest.raises(ValueError, match="must be nonempty"):
        source_visit_exposure_id("run", None, "target")
