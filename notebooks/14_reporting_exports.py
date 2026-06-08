# Databricks notebook source
# MAGIC %md
# MAGIC # 14 Reporting Exports
# MAGIC
# MAGIC Writes the final reporting manifest over all materialized workflow outputs.

# COMMAND ----------
from telegram_descriptive.notebook import create_standard_widgets, print_manifest, project_config_from_widgets
from telegram_descriptive.pipeline import run_stage

create_standard_widgets()
config = project_config_from_widgets()
result = run_stage("14", spark, config)  # noqa: F821
print_manifest(result)

