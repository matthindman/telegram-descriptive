# Databricks notebook source
# MAGIC %md
# MAGIC # 11 Link and Forwarding Networks
# MAGIC
# MAGIC Extracts organic URL/forward/reply/quote edges and writes network summaries.

# COMMAND ----------
from telegram_descriptive.notebook import create_standard_widgets, print_manifest, project_config_from_widgets
from telegram_descriptive.pipeline import run_stage

create_standard_widgets()
config = project_config_from_widgets()
result = run_stage("11", spark, config)  # noqa: F821
print_manifest(result)

