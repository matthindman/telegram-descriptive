# Databricks notebook source
# MAGIC %md
# MAGIC # 11 Link and Forwarding Networks
# MAGIC
# MAGIC Build organic URL, forwarding, reply, and quote graphs separately from the crawl transition graph.

# COMMAND ----------
from telegram_descriptive.networks.communities import degree_summary
from telegram_descriptive.networks.forwards import forwarding_edges
from telegram_descriptive.networks.links import url_edges
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest

create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
demo_edges = url_edges([{"channel_id": "c1", "post_uid": "p1", "urls": ["https://example.com/a"]}])
demo_edges.extend(forwarding_edges([{"channel_id": "c1", "post_uid": "p2", "shared_id": "c2"}]))
manifest = stage_manifest(
    "11_link_forwarding_networks",
    config,
    {
        "inputs": [config.outputs.fqtn("gold_message_analysis_frame"), config.outputs.fqtn("gold_channel_analysis_frame")],
        "planned_output": config.outputs.fqtn("silver_telegram_edges"),
        "demo_degree_summary": {k: dict(v) for k, v in degree_summary(demo_edges).items()},
    },
)
print_manifest(manifest)

