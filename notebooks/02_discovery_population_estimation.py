# Databricks notebook source
# MAGIC %md
# MAGIC # 02 Discovery Population Estimation
# MAGIC
# MAGIC Computes random-walk discovery estimates when exposure lineage exists; otherwise writes no-claim gap estimates.

# COMMAND ----------
from telegram_descriptive.notebook import create_standard_widgets, print_manifest, project_config_from_widgets
from telegram_descriptive.pipeline import run_stage

create_standard_widgets()
config = project_config_from_widgets()
result = run_stage("02", spark, config)  # noqa: F821
print_manifest(result)

