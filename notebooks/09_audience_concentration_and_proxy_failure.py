# Databricks notebook source
# MAGIC %md
# MAGIC # 09 Audience, Concentration, and Proxy Failure
# MAGIC
# MAGIC Summarize concentration and member/view proxy divergence.

# COMMAND ----------
from telegram_descriptive.descriptive.concentration import concentration_ratio, gini, hhi
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest

create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
values = [100, 50, 25, 25]
manifest = stage_manifest(
    "09_audience_concentration_and_proxy_failure",
    config,
    {
        "inputs": [
            config.outputs.fqtn("gold_channel_analysis_frame"),
            config.outputs.fqtn("gold_population_estimates"),
            config.outputs.fqtn("gold_too_sample_frame"),
        ],
        "metrics": {"gini": gini(values), "hhi": hhi(values), "top2_share": concentration_ratio(values, 2)},
    },
)
print_manifest(manifest)

