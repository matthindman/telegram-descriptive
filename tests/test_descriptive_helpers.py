from datetime import datetime, timezone

from telegram_descriptive.descriptive.composition import share_by_category
from telegram_descriptive.descriptive.posting import channel_posting_summary, parse_datetime


def test_parse_datetime_normalizes_naive_values_to_utc():
    parsed = parse_datetime("2026-01-02T03:04:05")

    assert parsed == datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_channel_posting_summary_handles_naive_and_aware_timestamps():
    rows = [
        {"canonical_channel_id": "c1", "published_at": "2026-01-01T00:00:00"},
        {"canonical_channel_id": "c1", "published_at": "2026-01-03T00:00:00Z"},
    ]

    summary = channel_posting_summary(rows, now=datetime(2026, 1, 5, tzinfo=timezone.utc))

    assert summary[0]["message_count"] == 2
    assert summary[0]["posts_per_day_observed"] == 2 / 3
    assert summary[0]["days_since_last_post"] == 2


def test_share_by_category_skips_negative_and_nonfinite_weights():
    shares = share_by_category(
        [
            {"topic": "news", "weight": 2},
            {"topic": "spam", "weight": -1},
            {"topic": "bad", "weight": float("nan")},
        ],
        category_col="topic",
        weight_col="weight",
    )

    assert shares == [{"category": "news", "value": 2.0, "share": 1.0}]
