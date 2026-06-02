# Databricks notebook source
# MAGIC %md
# MAGIC # 06 Language Detection
# MAGIC
# MAGIC Build source-aware text segments and aggregate segment-level language predictions.

# COMMAND ----------
from telegram_descriptive.language.aggregation import aggregate_language_predictions
from telegram_descriptive.language.segmentation import segment_record
from telegram_descriptive.notebook import create_text_widget, print_manifest, project_config_from_widgets, stage_manifest

create_text_widget("output_catalog", "dev_sean")
create_text_widget("output_schema", "matt")
create_text_widget("output_table_prefix", "telegram_descriptive")
create_text_widget("execution_mode", "manifest_only")

config = project_config_from_widgets()

# COMMAND ----------
demo_segments = segment_record(
    {"canonical_channel_id": "demo", "channel_name": "Noticias Demo", "post_content": "Noticias politicas de hoy"},
    entity_id_col="canonical_channel_id",
)
demo_predictions = [
    {"entity_id": segment.entity_id, "language": "es", "confidence": 0.8, "weight": segment.weight}
    for segment in demo_segments
]

manifest = stage_manifest(
    "06_language_detection",
    config,
    {
        "inputs": [config.outputs.fqtn("silver_messages"), config.outputs.fqtn("silver_channels")],
        "planned_outputs": [config.outputs.fqtn("silver_lid_segments"), "channel/message language labels"],
        "demo_aggregation": aggregate_language_predictions(demo_predictions),
    },
)
print_manifest(manifest)

