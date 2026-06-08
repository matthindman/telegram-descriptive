# Databricks notebook source
# MAGIC %md
# MAGIC # 03 Rank-Tail Denominators
# MAGIC
# MAGIC Builds ranked metric tables and writes D0-D3 rank-tail denominator estimates.

# COMMAND ----------
from telegram_descriptive.notebook import create_standard_widgets, print_manifest, project_config_from_widgets
from telegram_descriptive.pipeline import run_stage

create_standard_widgets()
config = project_config_from_widgets()
result = run_stage("03", spark, config)  # noqa: F821
print_manifest(result)

