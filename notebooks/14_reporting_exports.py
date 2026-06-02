# Databricks notebook source
# MAGIC %md
# MAGIC # 14 Reporting Exports
# MAGIC
# MAGIC Produce versioned methods tables, main figures, appendix figures, and safe aggregate exports.

# COMMAND ----------
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest
from telegram_descriptive.reporting.tables import methods_table

create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
manifest = stage_manifest(
    "14_reporting_exports",
    config,
    {
        "inputs": [
            config.outputs.fqtn("gold_too_sample_frame"),
            config.outputs.fqtn("gold_channel_analysis_frame"),
            config.outputs.fqtn("gold_message_analysis_frame"),
            config.outputs.fqtn("gold_population_estimates"),
            config.outputs.fqtn("gold_validation_summaries"),
        ],
        "planned_exports": [
            "methods tables",
            "main descriptive figures",
            "appendix figures",
            "data dictionary",
            "population and coverage package",
        ],
        "demo_methods_table": methods_table(
            [
                {
                    "estimand": "audience mass",
                    "metric_name": "follower_count",
                    "threshold": 10000,
                    "model": "D0",
                    "observed_n": 100,
                    "estimate": 120,
                    "lower_ci": 110,
                    "upper_ci": 150,
                    "diagnostic_flags": [],
                }
            ]
        ),
    },
)
print_manifest(manifest)

