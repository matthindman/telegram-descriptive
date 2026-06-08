# Databricks notebook source
# MAGIC %md
# MAGIC # 09 Audience, Concentration, and Proxy Failure
# MAGIC
# MAGIC Writes audience and proxy-failure descriptive summaries from gold channel frames.

# COMMAND ----------
from telegram_descriptive.notebook import create_standard_widgets, print_manifest, project_config_from_widgets
from telegram_descriptive.pipeline import run_stage

create_standard_widgets()
config = project_config_from_widgets()
result = run_stage("09", spark, config)  # noqa: F821
print_manifest(result)

