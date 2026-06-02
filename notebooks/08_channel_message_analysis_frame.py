# Databricks notebook source
# MAGIC %md
# MAGIC # 08 Channel and Message Analysis Frame
# MAGIC
# MAGIC Create the reusable gold channel and message analysis frames.

# COMMAND ----------
from telegram_descriptive.descriptive.frames import normalize_message_rows
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest

create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
demo_message = normalize_message_rows(
    [{"post_uid": "p1", "channel_id": 123, "post_content": "hello", "shared_id": "source"}]
)
manifest = stage_manifest(
    "08_channel_message_analysis_frame",
    config,
    {
        "inputs": [
            config.outputs.fqtn("silver_channels"),
            config.outputs.fqtn("silver_messages"),
            config.outputs.fqtn("gold_too_sample_frame"),
            "language labels",
            "topic labels",
            "ingestion audit",
        ],
        "planned_outputs": [
            config.outputs.fqtn("gold_channel_analysis_frame"),
            config.outputs.fqtn("gold_message_analysis_frame"),
        ],
        "demo_message_normalization": demo_message,
    },
)
print_manifest(manifest)

