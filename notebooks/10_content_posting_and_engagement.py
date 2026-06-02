# Databricks notebook source
# MAGIC %md
# MAGIC # 10 Content, Posting, and Engagement
# MAGIC
# MAGIC Describe posting frequency, content-type composition, and engagement distributions.

# COMMAND ----------
from telegram_descriptive.descriptive.engagement import engagement_summary
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest

create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
manifest = stage_manifest(
    "10_content_posting_and_engagement",
    config,
    {
        "inputs": [config.outputs.fqtn("gold_message_analysis_frame"), config.outputs.fqtn("gold_channel_analysis_frame")],
        "demo_engagement": engagement_summary(
            [{"post_view_count": 100, "total_emoji_reactions": 5, "post_share_count": 2}]
        ),
    },
)
print_manifest(manifest)

