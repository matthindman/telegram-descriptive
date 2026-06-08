# Databricks notebook source
# MAGIC %md
# MAGIC # 07 Topic Taxonomy and Classification
# MAGIC
# MAGIC Builds compact channel evidence bundles and provisional Telegram-native topic labels.

# COMMAND ----------
from telegram_descriptive.notebook import create_standard_widgets, print_manifest, project_config_from_widgets
from telegram_descriptive.pipeline import run_stage

create_standard_widgets()
config = project_config_from_widgets()
result = run_stage("07", spark, config)  # noqa: F821
print_manifest(result)

