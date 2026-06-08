# Databricks notebook source
# MAGIC %md
# MAGIC # 10 Content, Posting, and Engagement
# MAGIC
# MAGIC Writes content-type, posting, and engagement summaries from gold message frames.

# COMMAND ----------
from telegram_descriptive.notebook import create_standard_widgets, print_manifest, project_config_from_widgets
from telegram_descriptive.pipeline import run_stage

create_standard_widgets()
config = project_config_from_widgets()
result = run_stage("10", spark, config)  # noqa: F821
print_manifest(result)

