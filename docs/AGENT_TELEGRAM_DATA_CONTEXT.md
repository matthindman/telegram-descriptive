# Agent Telegram Data Context

This is the concise agent-facing index for Telegram Databricks resources.
For full schema detail, load `databricks_telegram_resources.agent.json`.
For researcher-facing context, load `README_telegram_data_resources.md`.

## Scope

Catalog: `prod_tads`

Schemas:

- `telegram`: general/base Telegram collection surfaces.
- `telegram_random_walk`: random-walk collection area.
- `telegram_too`: Top-of-the-Ocean Telegram collection area and the best
  starting point for descriptive post/channel analysis.

Probe date: 2026-06-01 UTC.

The probe was metadata-oriented. It did not run counts or broad table scans.
Small `telegram_too.tg_gd_*` aggregate checks found 29,099,371 posts,
1,662 channels, zero comments in the collection summary, 177 provisional
language values, a scrape window from 2026-02-26 to 2026-03-04, and a
publication range from 2015-09-20 to 2026-03-04.

## Best Starting Tables

Use `prod_tads.telegram_too` for most descriptive analysis:

- Channels: `prod_tads.telegram_too.tg_sl_channels`
- Channel metrics: `prod_tads.telegram_too.tg_sl_channels_metrics`
- Posts/messages: `prod_tads.telegram_too.tg_sl_posts`
- Post metrics: `prod_tads.telegram_too.tg_sl_posts_metrics`
- Comments: `prod_tads.telegram_too.tg_sl_comments`
- Comment metrics: `prod_tads.telegram_too.tg_sl_comments_metrics`
- Gold QA aggregates: `prod_tads.telegram_too.tg_gd_*`

Use `prod_tads.telegram_random_walk.tg_bz_ingest` and
`prod_tads.telegram_random_walk.tg_bz_ingest_log` as the visible raw random-walk
sources. No clean walk-event, edge-list, exposure, chain, or validation tables
were visible in the probed schemas.

## Important Columns

Channel metadata:

- `channel_id`
- `channel_name`
- `channel_url`
- `channel_url_external`
- `language_code`
- `detected_language`
- `first_ingestion_timestamp`
- `last_ingestion_timestamp`
- `first_scrape_timestamp`
- `scrape_timestamp`
- `scrape_date`
- `ingest_id`

Channel metrics:

- `follower_count`: likely Telegram member/subscriber metric; confirm semantics.
- `views_count`: channel-level view metric; confirm semantics.
- `post_count`
- `comment_count`
- `like_count`
- `share_count`
- `following_count`
- `scrape_timestamp`
- `ingestion_timestamp`

Posts:

- `post_uid`
- `channel_id`
- `post_type`
- `post_content`
- `post_title`
- `all_text`
- `searchable_text`
- `image_text`
- `ocr_data`
- `transcript_text`
- `hashtags`
- `post_link`
- `url`
- `media_url`
- `created_at`
- `published_at`
- `first_scrape_timestamp`
- `last_scrape_timestamp`
- `detected_language`
- `_translation_status`
- `quoted_id`
- `replied_id`
- `shared_id`
- `root_post_id`
- `repost_channel_data`

Post metrics:

- `post_uid`
- `channel_id`
- `post_view_count`
- `post_share_count`
- `post_comment_count`
- `post_like_count`
- `total_emoji_reactions`
- many individual `*_reactions` columns
- `scrape_timestamp`
- `ingestion_timestamp`

Random-walk bronze extras:

- `depth`
- `error`
- `id`
- `messages`
- `parentId`
- `status`
- `timestamp`

## Join Cautions

- `tg_sl_posts.channel_id` is `bigint`; related channel/metric tables use
  `string`. Cast explicitly.
- Metrics tables are time series. Build latest/max/windowed snapshot tables
  before joining to avoid row multiplication.
- `detected_language` exists but is not a validated LID v3 replacement.
- Reaction fields appear as structs, maps, and exploded columns depending on
  layer/schema. Normalize reactions before analysis.
- Gold `tg_gd_*` tables are derived QA/dashboard aggregates, not estimator
  source tables.
- The TOO corpus is post-volume skewed: the `> 2000` posts/channel bucket
  contains 1,120 channels and about 98.8% of posts. Report channel-weighted and
  post-weighted results separately.
- The provisional `NO TEXT` language bucket is large, about 23.9% of posts in
  the gold language aggregate. LID needs explicit no-text/media-heavy handling.
- Most TOO posts are historical backfill: about 74.1% are more than one year
  older than scrape time in the gold freshness aggregate.

## Tables The Analysis Still Needs To Build

- `silver_channel_metric_snapshots`
- `silver_post_metric_snapshots`
- `silver_telegram_edges`
- `silver_random_walk_events`
- `silver_random_walk_exposures`
- `silver_random_walk_validations`
- `silver_ranked_metrics`
- `gold_channel_analysis_frame`
- `gold_message_analysis_frame`
- `gold_population_estimates`
- `gold_too_sample_frame`

## Databricks Defaults

Existing repo defaults:

- `DATABRICKS_CONFIG_PROFILE=hindman.gmail.com@auth.researchaccelerator.org`
- `DATABRICKS_CLUSTER_ID=0303-193859-1ff54asc`
- Python env: `youtube_descriptive/.venv`

Use `scripts/telegram_databricks_resource_probe.py` to refresh the manifest.
