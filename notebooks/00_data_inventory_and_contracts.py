# Databricks notebook source
# MAGIC %md
# MAGIC # 00 Data Inventory, Contracts, and Canonical Silver Tables
# MAGIC
# MAGIC Inventories source tables, writes core silver channel/message/metric tables, and records contract context.

# COMMAND ----------
from telegram_descriptive.notebook import create_standard_widgets, print_manifest, project_config_from_widgets
from telegram_descriptive.pipeline import run_stage

create_standard_widgets()
config = project_config_from_widgets()
result = run_stage("00", spark, config)  # noqa: F821
print_manifest(result)

