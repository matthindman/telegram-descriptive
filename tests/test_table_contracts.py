from telegram_descriptive.qc import check_contract_columns
from telegram_descriptive.schemas import CONTRACTS, get_contract
from telegram_descriptive.config import OutputTables
from telegram_descriptive.tables import canonical_channel_id, rank_metric_rows


def test_contract_registry_contains_planned_gold_tables():
    assert "gold_too_sample_frame" in CONTRACTS
    assert "gold_population_estimates" in CONTRACTS


def test_contract_registry_matches_output_manifest():
    planned = set(OutputTables().planned_tables)

    assert planned <= set(CONTRACTS)


def test_contract_column_check_reports_missing_required_columns():
    contract = get_contract("silver_ranked_metrics")
    result = check_contract_columns(contract, ["ranking_version", "metric_name", "rank"])

    assert not result.ok
    assert "canonical_channel_id" in result.missing_required_columns
    assert "metric_value" in result.missing_required_columns


def test_canonical_channel_id_and_rank_metric_rows():
    assert canonical_channel_id(123) == "123"
    assert canonical_channel_id(" null ") is None

    ranked = rank_metric_rows(
        [
            {"channel_id": 1, "followers": 10},
            {"channel_id": "1", "followers": 12},
            {"channel_id": 2, "followers": 20},
            {"channel_id": 3, "followers": -5},
        ],
        channel_col="channel_id",
        metric_col="followers",
        ranking_version="test",
    )

    assert [row["canonical_channel_id"] for row in ranked] == ["2", "1"]
    assert [row["rank"] for row in ranked] == [1, 2]
