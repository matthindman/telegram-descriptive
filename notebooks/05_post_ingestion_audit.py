# Databricks notebook source
# MAGIC %md
# MAGIC # 05 Post-Ingestion Audit
# MAGIC
# MAGIC Confirm selected TOO channels have usable message-level data and metric fields.

# COMMAND ----------
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest

create_text_widget("source_catalog", "prod_tads")
create_text_widget("too_schema", "telegram_too")
create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
manifest = stage_manifest(
    "05_post_ingestion_audit",
    config,
    {
        "inputs": [
            config.outputs.fqtn("gold_too_sample_frame"),
            config.sources.too_posts,
            config.sources.too_post_metrics,
            config.sources.too_channels,
            config.sources.too_channel_metrics,
        ],
        "planned_outputs": [
            "channel ingestion status",
            "date coverage by channel",
            "field completeness report",
        ],
    },
)
print_manifest(manifest)

