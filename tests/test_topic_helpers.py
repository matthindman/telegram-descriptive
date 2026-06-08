from telegram_descriptive.topics.classification import validate_topic_key


def test_validate_topic_key_clamps_nonfinite_confidence():
    result = validate_topic_key({"topic_key": "not_real", "confidence": float("nan")})

    assert result["topic_key"] == "mixed_unknown"
    assert result["confidence"] == 0.0
