# Databricks notebook source
# MAGIC %md
# MAGIC # 00 Data Inventory and Contracts
# MAGIC
# MAGIC Establish source availability, planned table contracts, join cautions, and gaps before downstream analysis.

# COMMAND ----------
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest
from telegram_descriptive.schemas import CONTRACTS

create_text_widget("source_catalog", "prod_tads")
create_text_widget("telegram_schema", "telegram")
create_text_widget("random_walk_schema", "telegram_random_walk")
create_text_widget("too_schema", "telegram_too")
create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
source_manifest = {
    "too_channels": config.sources.too_channels,
    "too_channel_metrics": config.sources.too_channel_metrics,
    "too_posts": config.sources.too_posts,
    "too_post_metrics": config.sources.too_post_metrics,
    "random_walk_raw": config.sources.random_walk_raw,
    "random_walk_log": config.sources.random_walk_log,
}

contract_manifest = {name: contract.as_dict() for name, contract in CONTRACTS.items()}

manifest = stage_manifest(
    "00_data_inventory_and_contracts",
    config,
    {
        "source_tables": source_manifest,
        "contracts": contract_manifest,
        "join_cautions": [
            "Cast tg_sl_posts.channel_id to string before channel joins.",
            "Build metric snapshots before joining time-series metrics.",
            "Do not use tg_gd_* dashboard aggregates as estimator source tables.",
            "Keep channel-weighted and post-weighted summaries separate.",
        ],
    },
)
print_manifest(manifest)

# COMMAND ----------
# In smoke/core/full mode, extend this cell with Spark metadata scans:
# DESCRIBE TABLE, row counts, null rates, timestamp ranges, and contract checks.

