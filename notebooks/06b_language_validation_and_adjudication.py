# Databricks notebook source
# MAGIC %md
# MAGIC # 06b Language Validation and Adjudication
# MAGIC
# MAGIC Validate LID predictions, create review queues, and merge adjudicated labels.

# COMMAND ----------
from telegram_descriptive.language.validation import precision_recall_by_label
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest

create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
demo_validation = precision_recall_by_label(
    [
        {"adjudicated_language": "en", "language_label": "en"},
        {"adjudicated_language": "es", "language_label": "en"},
    ]
)

manifest = stage_manifest(
    "06b_language_validation_and_adjudication",
    config,
    {
        "inputs": [config.outputs.fqtn("silver_lid_segments"), "language review/adjudication tables"],
        "planned_output": config.outputs.fqtn("gold_validation_summaries"),
        "demo_validation": demo_validation,
    },
)
print_manifest(manifest)

