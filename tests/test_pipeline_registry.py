from telegram_descriptive.config import OutputTables
from telegram_descriptive.config import ProjectConfig
from telegram_descriptive.pipeline.spark_stages import STAGE_DISPATCH, STAGE_NAMES
from telegram_descriptive.pipeline.spark_stages import run_stage
from telegram_descriptive.pipeline.spark_stages import _sql_literal
from telegram_descriptive.schemas import CONTRACTS


def test_every_stage_has_dispatch_and_name():
    expected = {"00", "01", "02", "03", "04", "05", "06", "06b", "07", "08", "09", "10", "11", "12", "13", "14"}

    assert expected <= set(STAGE_DISPATCH)
    assert expected <= set(STAGE_NAMES)


def test_every_planned_output_has_contract():
    planned = set(OutputTables().planned_tables)

    assert planned <= set(CONTRACTS)


def test_manifest_only_stage_does_not_require_spark():
    result = run_stage("00", spark=None, config=ProjectConfig())

    assert result["status"] == "manifest_only_no_source_reads_or_writes"
    assert "silver_channels" in result["output_tables"]


def test_sql_literal_escapes_quotes_for_replace_where():
    assert _sql_literal("run'1") == "'run''1'"
