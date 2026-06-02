# Databricks notebook source
# MAGIC %md
# MAGIC # 02 Discovery Population Estimation
# MAGIC
# MAGIC Estimate reachable public channel-count completeness only when exposure lineage exists.

# COMMAND ----------
from telegram_descriptive.estimation.chao import chao2
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest
from telegram_descriptive.qc import gap_report

create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
required_inputs = [
    config.outputs.fqtn("silver_random_walk_exposures"),
    config.outputs.fqtn("silver_random_walk_events"),
    config.outputs.fqtn("silver_random_walk_validations"),
]

manifest = stage_manifest(
    "02_discovery_population_estimation",
    config,
    {
        "required_inputs": required_inputs,
        "gap_policy": gap_report(
            "discovery_population_estimation",
            required_inputs=required_inputs,
            observed_inputs=[],
            reason="The 2026-06-01 probe did not find clean exposure, validation, or chain tables.",
        ),
        "estimator": "Chao2 plus saturation and monotone threshold survival once inputs exist.",
        "local_smoke_example": chao2([{"a", "b"}, {"b", "c"}]).__dict__,
    },
)
print_manifest(manifest)

