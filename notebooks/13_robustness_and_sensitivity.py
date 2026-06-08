# Databricks notebook source
# MAGIC %md
# MAGIC # 13 Robustness and Sensitivity
# MAGIC
# MAGIC Writes robustness checks over thresholds, exclusions, and data-availability scenarios.

# COMMAND ----------
from telegram_descriptive.notebook import create_standard_widgets, print_manifest, project_config_from_widgets
from telegram_descriptive.pipeline import run_stage

create_standard_widgets()
config = project_config_from_widgets()
result = run_stage("13", spark, config)  # noqa: F821
print_manifest(result)

