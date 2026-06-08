# Databricks notebook source
# MAGIC %md
# MAGIC # 06 Language Detection
# MAGIC
# MAGIC Builds source-aware LID segments and provisional channel/message language labels.

# COMMAND ----------
from telegram_descriptive.notebook import create_standard_widgets, print_manifest, project_config_from_widgets
from telegram_descriptive.pipeline import run_stage

create_standard_widgets()
config = project_config_from_widgets()
result = run_stage("06", spark, config)  # noqa: F821
print_manifest(result)

