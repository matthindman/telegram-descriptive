# Databricks notebook source
# MAGIC %md
# MAGIC # 12 Missed-Audience Sensitivity
# MAGIC
# MAGIC Assess dark-audience omission sensitivity from organic graph and crawl path diagnostics.

# COMMAND ----------
from telegram_descriptive.networks.missed_audience import dark_audience_bound
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest

create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
manifest = stage_manifest(
    "12_missed_audience_sensitivity",
    config,
    {
        "inputs": [
            config.outputs.fqtn("silver_telegram_edges"),
            config.outputs.fqtn("silver_random_walk_events"),
            config.outputs.fqtn("gold_channel_analysis_frame"),
        ],
        "kappa_grid": [1, 10, 30, 100, "infinity"],
        "demo_bound": dark_audience_bound(1000, 0.05, 10),
    },
)
print_manifest(manifest)

