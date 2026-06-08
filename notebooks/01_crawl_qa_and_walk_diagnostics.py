# Databricks notebook source
# MAGIC %md
# MAGIC # 01 Crawl QA and Walk Diagnostics
# MAGIC
# MAGIC Materializes random-walk QA rows where possible and writes explicit lineage gap outputs otherwise.

# COMMAND ----------
from telegram_descriptive.notebook import create_standard_widgets, print_manifest, project_config_from_widgets
from telegram_descriptive.pipeline import run_stage

create_standard_widgets()
config = project_config_from_widgets()
result = run_stage("01", spark, config)  # noqa: F821
print_manifest(result)

