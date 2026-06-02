# Databricks notebook source
# MAGIC %md
# MAGIC # 01 Crawl QA and Walk Diagnostics
# MAGIC
# MAGIC Audit whether visible random-walk sources can reconstruct walk events, validations, and exposures.

# COMMAND ----------
from telegram_descriptive.crawl.contracts import visible_bronze_gap_summary
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest

create_text_widget("source_catalog", "prod_tads")
create_text_widget("random_walk_schema", "telegram_random_walk")
create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
gap_summary = visible_bronze_gap_summary()
manifest = stage_manifest(
    "01_crawl_qa_and_walk_diagnostics",
    config,
    {
        "inputs": [config.sources.random_walk_raw, config.sources.random_walk_log],
        "planned_outputs": [
            config.outputs.fqtn("silver_random_walk_events"),
            config.outputs.fqtn("silver_random_walk_exposures"),
            config.outputs.fqtn("silver_random_walk_validations"),
        ],
        "visible_bronze_gap_summary": gap_summary,
    },
)
print_manifest(manifest)

# COMMAND ----------
# This notebook must emit a gap report instead of population estimates unless
# chain IDs, candidate targets, validation outcomes, and duplicate-collapsed exposures are available.

