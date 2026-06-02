# Telegram Descriptive Data Contracts

This document summarizes the table contracts implemented in
`telegram_descriptive.schemas`. The source of truth is the Python contract
registry so tests and notebooks can validate against the same definitions.

## Contract Principles

- One row grain per table.
- Explicit primary keys and join surfaces.
- Metric time series are snapshotted before joins.
- Channel and post/message tables do not mix grains.
- Observed facts, inferred quantities, and validation/adjudication outputs are
  stored in separate columns.

## Planned Silver Tables

- `silver_channels`: one canonical channel/group row with eligibility, metadata,
  current best follower count, observation timestamps, provenance, and quality
  flags.
- `silver_channel_metric_snapshots`: one row per channel per metric snapshot
  policy, built from `tg_sl_channels_metrics`.
- `silver_messages`: one ingested message/post with normalized text fields,
  content indicators, forwarding/reply flags, and quality flags.
- `silver_post_metric_snapshots`: one row per post per metric snapshot policy,
  built from `tg_sl_posts_metrics`.
- `silver_telegram_edges`: organic URL, forward, quote, reply, mention, hashtag,
  or other network edges. Artificial crawl restarts and walkbacks are excluded.
- `silver_random_walk_events`: crawl transition events. This remains blocked
  unless crawler lineage can be reconstructed or supplied.
- `silver_random_walk_exposures`: duplicate-collapsed eligible target exposures.
  This is required for discovery estimation and must not be fabricated from
  incomplete lineage.
- `silver_ranked_metrics`: deduplicated channel rankings by metric and version.
- `silver_lid_segments`: source-aware text segments and language predictions.
- `silver_topic_inputs`: compact channel/message evidence bundles for topic
  classification.

## Planned Gold Tables

- `gold_too_sample_frame`: final and candidate TOO membership, selection rules,
  metric ranks, coverage estimates, and post-ingestion status.
- `gold_channel_analysis_frame`: channel-level descriptive frame with member/view
  metrics, labels, activity, content mix, network features, and provenance.
- `gold_message_analysis_frame`: message-level descriptive frame with content,
  engagement, language/topic labels, and channel covariates.
- `gold_population_estimates`: discovery, rank-tail, denominator, bootstrap,
  coverage, and diagnostic outputs by version.
- `gold_validation_summaries`: language, topic, eligibility, and table-quality
  validation summaries.

## Known Blocking Gap

The 2026-06-01 Databricks probe did not find clean random-walk event, exposure,
validation, chain, or seed tables. Notebooks 01 and 02 therefore default to a
structured gap report. Population-count completeness estimates should only run
after those inputs exist.

