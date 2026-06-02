from telegram_descriptive.language.aggregation import aggregate_language_predictions
from telegram_descriptive.language.segmentation import best_text_for_message, segment_record


def test_segment_record_keeps_source_weights():
    segments = segment_record(
        {
            "canonical_channel_id": "c1",
            "channel_name": "Noticias",
            "post_content": "Noticias de politica nacional",
            "image_text": "Texto en imagen",
        },
        entity_id_col="canonical_channel_id",
    )

    fields = {segment.source_field for segment in segments}
    assert {"channel_name", "post_content", "image_text"} <= fields
    assert all(segment.entity_id == "c1" for segment in segments)


def test_best_text_deduplicates_sources():
    text = best_text_for_message({"post_content": "hello", "all_text": "hello", "image_text": "image words"})

    assert text == "hello\nimage words"


def test_aggregate_language_predictions_marks_mixed_when_margin_small():
    labels = aggregate_language_predictions(
        [
            {"entity_id": "c1", "language": "en", "confidence": 0.9, "weight": 1.0},
            {"entity_id": "c1", "language": "es", "confidence": 0.85, "weight": 1.0},
        ],
        mixed_margin=0.2,
    )

    assert labels[0]["language_label"] == "MIXED"
    assert labels[0]["language_segment_count"] == 2

