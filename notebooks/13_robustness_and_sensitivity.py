# Databricks notebook source
# MAGIC %md
# MAGIC # 13 Robustness and Sensitivity
# MAGIC
# MAGIC Centralize sensitivity checks across estimator boundaries, sample cuts, labels, and exclusions.

# COMMAND ----------
from telegram_descriptive.descriptive.robustness import robustness_matrix
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest

create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
manifest = stage_manifest(
    "13_robustness_and_sensitivity",
    config,
    {
        "inputs": ["outputs from notebooks 02-12"],
        "planned_output": "robustness matrix and appendix tables",
        "demo_matrix": robustness_matrix([{"check": "boundary", "baseline": 0.8, "alternative": 0.76}]),
    },
)
print_manifest(manifest)

