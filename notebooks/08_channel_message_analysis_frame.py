# Databricks notebook source
# MAGIC %md
# MAGIC # 08 Channel and Message Analysis Frame
# MAGIC
# MAGIC Builds reusable gold channel and message analysis frames.

# COMMAND ----------
from telegram_descriptive.notebook import create_standard_widgets, print_manifest, project_config_from_widgets
from telegram_descriptive.pipeline import run_stage

create_standard_widgets()
config = project_config_from_widgets()
result = run_stage("08", spark, config)  # noqa: F821
print_manifest(result)

