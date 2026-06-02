# Databricks notebook source
# MAGIC %md
# MAGIC # 07 Topic Taxonomy and Classification
# MAGIC
# MAGIC Define Telegram-native topics and classify channels from compact evidence bundles.

# COMMAND ----------
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest
from telegram_descriptive.topics.classification import rule_based_topic, validate_topic_key
from telegram_descriptive.topics.taxonomy import TELEGRAM_TOPICS_V1

create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
demo_topic = validate_topic_key(rule_based_topic("daily bitcoin and crypto trading news"))
manifest = stage_manifest(
    "07_topic_taxonomy_and_classification",
    config,
    {
        "inputs": [
            config.outputs.fqtn("silver_topic_inputs"),
            "post_embeddings",
            "subsample_items provisional enrichments",
        ],
        "taxonomy_version": config.analysis.topic_taxonomy_version,
        "topic_count": len(TELEGRAM_TOPICS_V1),
        "planned_outputs": ["topic prediction table", "topic review queue"],
        "demo_topic": demo_topic,
    },
)
print_manifest(manifest)

