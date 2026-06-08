# Databricks notebook source
# MAGIC %md
# MAGIC # 06b Language Validation and Adjudication
# MAGIC
# MAGIC Writes validation summaries and review-status rows for provisional language labels.

# COMMAND ----------
from telegram_descriptive.notebook import create_standard_widgets, print_manifest, project_config_from_widgets
from telegram_descriptive.pipeline import run_stage

create_standard_widgets()
config = project_config_from_widgets()
result = run_stage("06b", spark, config)  # noqa: F821
print_manifest(result)

