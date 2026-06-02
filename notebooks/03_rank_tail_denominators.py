# Databricks notebook source
# MAGIC %md
# MAGIC # 03 Rank-Tail Denominators
# MAGIC
# MAGIC Build ranked member/view metrics and fit D0-D3 tail denominator scenarios.

# COMMAND ----------
from telegram_descriptive.estimation.rank_tail import estimate_tail_ladder
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest

create_text_widget("source_catalog", "prod_tads")
create_text_widget("too_schema", "telegram_too")
create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
demo_values = [10_000 / (rank**1.25) for rank in range(1, 301)]
demo_estimates = [
    {"model": est.model, "tail_mass": est.tail_mass, "total_mass": est.total_mass, "flags": list(est.flags)}
    for est in estimate_tail_ladder(demo_values, boundary_rank=100, fitting_window=50)
]

manifest = stage_manifest(
    "03_rank_tail_denominators",
    config,
    {
        "inputs": [config.sources.too_channel_metrics, config.sources.too_post_metrics],
        "planned_output": config.outputs.fqtn("gold_population_estimates"),
        "ranked_metrics_output": config.outputs.fqtn("silver_ranked_metrics"),
        "candidate_metrics": ["follower_count", "views_count", "post_view_count_aggregate"],
        "demo_tail_ladder": demo_estimates,
    },
)
print_manifest(manifest)

