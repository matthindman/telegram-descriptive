# Databricks notebook source
# MAGIC %md
# MAGIC # 05 Post-Ingestion Audit
# MAGIC
# MAGIC Audits selected-channel message and metric availability before gold frame construction.

# COMMAND ----------
from telegram_descriptive.notebook import create_standard_widgets, print_manifest, project_config_from_widgets
from telegram_descriptive.pipeline import run_stage

create_standard_widgets()
config = project_config_from_widgets()
result = run_stage("05", spark, config)  # noqa: F821
print_manifest(result)

