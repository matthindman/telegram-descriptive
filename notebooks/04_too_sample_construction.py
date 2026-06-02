# Databricks notebook source
# MAGIC %md
# MAGIC # 04 TOO Sample Construction
# MAGIC
# MAGIC Choose and document candidate high-reach samples with coverage estimates and caveats.

# COMMAND ----------
from telegram_descriptive.estimation.coverage import coverage
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest

create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
manifest = stage_manifest(
    "04_too_sample_construction",
    config,
    {
        "inputs": [
            config.outputs.fqtn("silver_ranked_metrics"),
            config.outputs.fqtn("gold_population_estimates"),
        ],
        "planned_output": config.outputs.fqtn("gold_too_sample_frame"),
        "decision_points": [
            "member/subscriber metric versus view metric",
            "coverage target and tolerance",
            "headline denominator scenario D0-D3",
        ],
        "coverage_example": coverage(800, 1000),
    },
)
print_manifest(manifest)

