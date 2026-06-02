# Telegram Databricks Data Resource Context

_Generated from lightweight Databricks/Unity Catalog metadata on 2026-06-01
using Databricks profile `hindman.gmail.com@auth.researchaccelerator.org` and
cluster `0303-193859-1ff54asc`._

Machine-readable companion:

- `databricks_telegram_resources.agent.json` contains the schema manifest
  collected by `scripts/telegram_databricks_resource_probe.py`.

This document is for researchers and coding agents working on the Telegram
descriptive analysis. It describes the relevant `prod_tads` schemas, table
families, important variable names, join keys, and current gaps for the planned
analysis.

## Scope and Query Safety

The probe covered these Unity Catalog schemas:

- `prod_tads.telegram`
- `prod_tads.telegram_random_walk`
- `prod_tads.telegram_too`

The probe intentionally avoided full data scans. It collected table lists,
schemas, column role hints, and Delta metadata where available. It did not run
table counts or broad value profiles. Many of the public `tg_sl_*` and
`tg_bz_*` surfaces are materialized views; `DESCRIBE DETAIL` is table-only and
therefore fails on those views, but schema introspection succeeds.

Practical implication: use this document as an orientation map, then run
targeted table-specific QA inside Databricks when you need counts, null rates,
date ranges, or metric distributions.

## High-Level Schema Roles

| Schema | Visible resources | Role |
|---|---:|---|
| `prod_tads.telegram` | 10 | General Telegram ingest and shaped post/channel/comment tables. Older or base Telegram collection area. |
| `prod_tads.telegram_random_walk` | 12 | Random-walk Telegram collection area. Has the same shaped Telegram surfaces plus random-walk-ish raw fields in bronze. Explicit edge/exposure/chain tables were not visible in the probed schemas. |
| `prod_tads.telegram_too` | 22 | Top-of-the-Ocean Telegram collection area. Has bronze/silver/gold surfaces, embeddings, sampling tables, and dashboard-style aggregates. This is the most complete ready-to-analyze schema for post/channel descriptive work. |

## Lightweight Aggregate Findings

These checks read small `telegram_too.tg_gd_*` aggregate tables, not the raw
post tables.

`prod_tads.telegram_too.tg_gd_collection_summary` currently reports:

- `total_posts`: 29,099,371
- `total_channels`: 1,662
- `total_comments`: 0
- `earliest_scrape`: 2026-02-26 12:45:20
- `latest_scrape`: 2026-03-04 18:53:32
- `total_scrape_span_hours`: 150.136667
- `active_scrape_minutes`: 599
- `peak_minute_posts`: 144,773
- `distinct_languages`: 177
- `earliest_published`: 2015-09-20 22:14:24
- `latest_published`: 2026-03-04 17:00:00

Interpretation:

- The TOO table is large enough that raw scans should be deliberate.
- The scrape window is short relative to the publication history, so this is a
  large historical backfill rather than only a real-time stream.
- The gold summary reports zero comments, despite comment tables existing. Any
  comment analysis must first verify actual comment coverage.

Top provisional `detected_language` values by post count:

| Language value | Posts | Percent |
|---|---:|---:|
| `ru` | 7,264,558 | 24.96 |
| `NO TEXT` | 6,956,227 | 23.91 |
| `fa` | 5,147,470 | 17.69 |
| `en` | 4,318,252 | 14.84 |
| `ar` | 1,095,604 | 3.77 |

Interpretation:

- Provisional language is dominated by Russian, no-text posts, Persian, and
  English.
- The very large `NO TEXT` share makes Telegram LID materially different from
  the YouTube channel-metadata problem; media/link-heavy channels need explicit
  handling.

Posts-per-channel histogram from `tg_gd_posts_per_channel_histogram`:

| Post bucket | Channels | Posts | Percent of posts |
|---|---:|---:|---:|
| `1` | 11 | 11 | 0.00004 |
| `2-5` | 33 | 94 | 0.00032 |
| `6-20` | 14 | 147 | 0.00051 |
| `21-100` | 42 | 2,667 | 0.00917 |
| `101-500` | 198 | 59,624 | 0.20490 |
| `501-2000` | 245 | 289,274 | 0.99409 |
| `> 2000` | 1,120 | 28,747,554 | 98.79098 |

Interpretation:

- Post volume is extremely concentrated in high-volume channels.
- Descriptive analyses should report channel-weighted and post-weighted results
  separately.
- Model training and validation samples should avoid being overwhelmed by the
  largest posting channels.

Freshness summary from `tg_gd_freshness_distribution`:

| Freshness bucket | Posts | Percent |
|---|---:|---:|
| `< 1 hour` | 247 | 0.00085 |
| `1-24 hours` | 20,287 | 0.06972 |
| `1-7 days` | 126,387 | 0.43433 |
| `1-4 weeks` | 382,174 | 1.31334 |
| `1-12 months` | 7,007,220 | 24.08031 |
| `> 1 year` | 21,563,055 | 74.10145 |
| `unknown` | 1 | 0.000003 |

Interpretation:

- Most collected posts are older than one year.
- Analyses of current attention or event responsiveness need a recency window,
  not the full historical post table by default.

## Databricks Environment

- Workspace host in the existing bundle dev target:
  `https://adb-7405612174002821.1.azuredatabricks.net`
- Existing Databricks Connect defaults in this repo:
  - `DATABRICKS_CONFIG_PROFILE=hindman.gmail.com@auth.researchaccelerator.org`
  - `DATABRICKS_CLUSTER_ID=0303-193859-1ff54asc`
- Existing Python environment:
  - `youtube_descriptive/.venv`
  - `databricks-connect>=17.3,<17.4`

Recommended access pattern:

```python
from databricks.connect import DatabricksSession
from databricks.sdk.core import Config

config = Config(
    profile="hindman.gmail.com@auth.researchaccelerator.org",
    cluster_id="0303-193859-1ff54asc",
)
spark = DatabricksSession.builder.sdkConfig(config).getOrCreate()
```

Do not put secrets in notebooks or docs. Use local Databricks profiles,
environment variables, or Databricks job configuration.

## Resource Summary

### `prod_tads.telegram`

| Table | Type from information schema | Columns | Role |
|---|---|---:|---|
| `sampling_history` | managed | 14 | Sampling/enrichment audit table. |
| `subsample_items` | managed | 31 | Item-level sampled content/enrichment table. |
| `tg_bz_ingest` | materialized view | 76 | Raw-ish Telegram ingest surface with nested channel data, comments, reactions, text, URLs, file/source metadata, and ingest timestamps. |
| `tg_bz_ingest_log` | materialized view | 12 | Ingest-file/source log. |
| `tg_sl_channels` | materialized view | 14 | Shaped channel metadata. |
| `tg_sl_channels_metrics` | materialized view | 12 | Channel metric time series. |
| `tg_sl_comments` | materialized view | 16 | Comment text and comment metadata. |
| `tg_sl_comments_metrics` | materialized view | 11 | Comment metrics and reactions. |
| `tg_sl_posts` | materialized view | 56 | Shaped post/message metadata and text fields. |
| `tg_sl_posts_metrics` | materialized view | 64 | Post metrics and exploded emoji reaction columns. |

### `prod_tads.telegram_random_walk`

| Table | Type from information schema | Columns | Role |
|---|---|---:|---|
| `post_embeddings` | managed | 3 | Embedding table; metadata indicates 0 files at probe time. |
| `sampling_history` | managed | 14 | Sampling/enrichment audit table. |
| `social_media_posts` | foreign | 0 via Spark schema | Managed vector index with Delta Sync. Not a normal analysis table. |
| `subsample_items` | managed | 31 | Item-level sampled content/enrichment table; metadata indicates 0 files at probe time. |
| `tg_bz_ingest` | streaming table | 83 | Random-walk bronze ingest. Includes normal Telegram post fields plus `depth`, `error`, `id`, `messages`, `parentId`, `status`, and `timestamp`. |
| `tg_bz_ingest_log` | materialized view | 11 | Ingest/source log. |
| `tg_sl_channels` | materialized view | 14 | Shaped channel metadata. |
| `tg_sl_channels_metrics` | materialized view | 12 | Channel metric time series. |
| `tg_sl_comments` | materialized view | 16 | Comment text and metadata. |
| `tg_sl_comments_metrics` | materialized view | 11 | Comment metrics and reactions. |
| `tg_sl_posts` | materialized view | 56 | Shaped post/message metadata and text fields. |
| `tg_sl_posts_metrics` | materialized view | 64 | Post metrics and exploded emoji reaction columns. |

### `prod_tads.telegram_too`

| Table | Type from information schema | Columns | Role |
|---|---|---:|---|
| `post_embeddings` | managed | 3 | Post embedding table with `embedding_1024`; about 8.1 GB by Delta metadata. Use selectively. |
| `sampling_history` | managed | 14 | Sampling/enrichment audit table. |
| `subsample_items` | managed | 31 | Item-level sampled content/enrichment table; about 504 MB by Delta metadata. |
| `tg_bz_ingest` | streaming table | 83 | TOO bronze ingest. Partitioned by `published_date`; about 7.7 GB by Delta metadata. |
| `tg_bz_ingest_log` | materialized view | 11 | Ingest/source log. |
| `tg_gd_ad_vs_organic_by_channel` | managed | 7 | Gold aggregate for ad/organic channel mix. |
| `tg_gd_channel_leaderboard` | managed | 9 | Gold channel leaderboard. |
| `tg_gd_collection_summary` | managed | 11 | Gold collection-level summary. |
| `tg_gd_emoji_reaction_by_language` | managed | 7 | Emoji reaction distribution by detected language. |
| `tg_gd_emoji_reaction_mix` | managed | 5 | Overall emoji reaction mix. |
| `tg_gd_freshness_distribution` | managed | 5 | Freshness/lag summary. |
| `tg_gd_hashtag_leaderboard` | managed | 4 | Hashtag leaderboard. |
| `tg_gd_ingestion_by_minute` | managed | 4 | Ingestion throughput by minute. |
| `tg_gd_language_distribution` | managed | 3 | Detected-language distribution. |
| `tg_gd_posts_per_channel_histogram` | managed | 6 | Posts-per-channel histogram. |
| `tg_gd_publication_timeline` | managed | 3 | Publication timeline by month. |
| `tg_sl_channels` | materialized view | 14 | Shaped channel metadata. |
| `tg_sl_channels_metrics` | materialized view | 12 | Channel metric time series. |
| `tg_sl_comments` | materialized view | 16 | Comment text and metadata. |
| `tg_sl_comments_metrics` | materialized view | 11 | Comment metrics and reactions. |
| `tg_sl_posts` | materialized view | 56 | Shaped post/message metadata and text fields. |
| `tg_sl_posts_metrics` | materialized view | 64 | Post metrics and exploded emoji reaction columns. |

## Ignore or Treat as Operational

`information_schema.tables` also exposes DLT/materialization internals:

- `__materialization_mat_*`
- `event_log_*`

These are useful for pipeline troubleshooting, not for the descriptive analysis.
Use the named public surfaces (`tg_bz_*`, `tg_sl_*`, `tg_gd_*`,
`sampling_history`, `subsample_items`, `post_embeddings`) for analysis.

## Core Analytical Surfaces

### Channel Metadata: `tg_sl_channels`

Grain: one shaped channel record per channel/ingest context.

Important columns:

- `channel_id`
- `channel_name`
- `channel_profile_image`
- `channel_url`
- `channel_url_external`
- `language_code`
- `detected_language`
- `first_ingestion_timestamp`
- `last_ingestion_timestamp`
- `first_scrape_timestamp`
- `scrape_timestamp`
- `scrape_date`
- `ingest_id_first_ingest`
- `ingest_id`

Use this table for channel identity, URLs, source language fields, and ingest
provenance. It does not contain channel audience metrics; join to
`tg_sl_channels_metrics`.

### Channel Metrics: `tg_sl_channels_metrics`

Grain: channel metric observations by `channel_id`, `ingest_id`, and scrape
time.

Important columns:

- `ingest_id`
- `channel_id`
- `scrape_timestamp`
- `ingestion_timestamp`
- `scrape_date`
- `follower_count`
- `following_count`
- `post_count`
- `comment_count`
- `like_count`
- `share_count`
- `views_count`

Likely metric mapping:

- Telegram subscriber/member audience proxy: `follower_count`
- Channel-level post/activity count: `post_count`
- Channel-level engagement/activity proxies: `views_count`, `like_count`,
  `share_count`, `comment_count`

Open semantic check: confirm whether `follower_count` is the Telegram channel
subscriber/member count for both channels and groups, and whether `views_count`
is a channel aggregate or a source-specific collected metric.

### Posts/Messages: `tg_sl_posts`

Grain: one shaped Telegram post/message record.

Important identifier/provenance columns:

- `post_uid`
- `channel_id`
- `ingest_id`
- `ingest_id_first_ingest`
- `post_link`
- `post_handle`
- `url`
- `media_url`
- `thumb_url`
- `list_ids`
- `project_ids`
- `search_term_ids`
- `segment_ids`

Important time columns:

- `created_at`
- `created_date`
- `published_at`
- `published_date`
- `first_ingestion_timestamp`
- `last_ingestion_timestamp`
- `first_scrape_timestamp`
- `last_scrape_timestamp`

Important text/content columns:

- `post_content`
- `post_title`
- `all_text`
- `searchable_text`
- `image_text`
- `ocr_data`
- `transcript_text`
- `hashtags`
- `post_type`
- `platform_name`
- `has_embed_media`
- `video_length`
- `language_code`
- `detected_language`
- `_translation_status`

Important reply/repost/linkage columns:

- `is_reply`
- `quoted_id`
- `replied_id`
- `shared_id`
- `root_post_id`
- `repost_channel_data`

Use this table for message/post text, publication dates, language inputs,
content-type features, hashtags, URL/link features, and reply/repost structure.

Type caveat: `tg_sl_posts.channel_id` appears as `bigint`, while
`tg_sl_channels.channel_id` and `tg_sl_posts_metrics.channel_id` appear as
`string`. Cast explicitly before joins.

### Post Metrics: `tg_sl_posts_metrics`

Grain: post metric observations by `post_uid`, `channel_id`, `ingest_id`, and
scrape time.

Important columns:

- `ingest_id`
- `channel_id`
- `post_uid`
- `published_at`
- `published_date`
- `scrape_timestamp`
- `ingestion_timestamp`
- `post_comment_count`
- `post_like_count`
- `post_share_count`
- `post_view_count`
- `total_emoji_reactions`
- individual `*_reactions` columns such as `thumbs_up_reactions`,
  `fire_reactions`, `thinking_face_reactions`, `folded_hands_reactions`,
  `cursing_face_reactions`, and many others.

Use this table for post-level views, shares/forwards if represented by
`post_share_count`, comments, likes, and reaction mix. The individual emoji
columns are convenient for aggregate reaction analysis but should be grouped
into semantically meaningful families before modeling.

Type caveat: several post metric count fields were role-tagged as identifiers
by the automated probe because their names contain `post`; treat
`post_comment_count`, `post_like_count`, `post_share_count`, and
`post_view_count` as metrics.

### Comments: `tg_sl_comments`

Grain: one shaped comment record.

Important columns:

- `comment_id`
- `comment_text`
- `comment_handle`
- `published_at`
- `published_date`
- `post_uid`
- `channel_id`
- `first_ingestion_timestamp`
- `last_ingestion_timestamp`
- `first_scrape_timestamp`
- `last_scrape_timestamp`
- `ingest_id_first_ingest`
- `ingest_id`
- `detected_language`
- `_translation_status`
- `hashtags`

Use this table only if comment coverage is sufficiently complete for the
research question. Comment availability may vary by channel, post, collection
method, and Telegram access rules.

### Comment Metrics: `tg_sl_comments_metrics`

Grain: comment metric observations by comment/post/channel/ingest context.

Important columns:

- `ingest_id`
- `channel_id`
- `post_uid`
- `comment_id`
- `published_at`
- `published_date`
- `scrape_timestamp`
- `ingestion_timestamp`
- `reactions`
- `reply_count`
- `view_count`

Reaction representation caveat:

- In `prod_tads.telegram`, bronze/comment reactions can be fixed structs with
  explicit emoji fields.
- In `prod_tads.telegram_random_walk` and `prod_tads.telegram_too`, bronze and
  comment metric reactions often appear as `map<string,bigint>`.
- Use helper functions that can normalize both structs and maps.

### Bronze Ingest: `tg_bz_ingest`

Grain: raw or near-raw ingested Telegram post/message records with nested
fields.

Important common fields:

- Post/channel identity: `post_uid`, `channel_id`, `channel_name`, `handle`,
  `post_link`, `url`
- Channel nested metadata: `channel_data`
- Text/content: `all_text`, `description`, `image_text`, `searchable_text`,
  `transcript_text`, `post_title`, `ocr_data`
- Engagement: `comment_count`, `comments_count`, `like_count`, `likes_count`,
  `share_count`, `shares_count`, `view_count`, `views_count`,
  `performance_scores`, `reactions`
- Nested comments: `comments`
- Source metadata: `file_name`, `file_path`, `file_size`, `sourcing_system`,
  `sampling_method`, `platform`, `ingest_id`
- Ingest/scrape status: `ingestion_timestamp`, `scrape_timestamp`,
  `sourcing_status`, `failure_reason`
- Partition: `published_date`

Random-walk and TOO bronze fields:

- `depth`
- `error`
- `id`
- `messages`
- `parentId`
- `status`
- `timestamp`

These extra fields are the only visible random-walk-like fields found in the
probed production schemas. They may be enough to derive parent-child crawl
relationships, but they are not a substitute for an explicit walk-event,
edge-list, exposure, or validation table.

## Gold Aggregate Tables in `telegram_too`

The `tg_gd_*` tables are useful for quick QA, dashboards, and sanity checks.
They should not replace row-level silver tables for estimator work.

| Table | Useful columns | Use |
|---|---|---|
| `tg_gd_collection_summary` | `total_posts`, `total_channels`, `total_comments`, `earliest_scrape`, `latest_scrape`, `earliest_published`, `latest_published`, `distinct_languages` | Collection-level sanity check. |
| `tg_gd_channel_leaderboard` | `channel_id`, `channel_name`, `post_count`, `first_published`, `last_published`, `active_days`, `primary_language`, `first_scraped`, `last_scraped` | Quick channel activity leaderboard. |
| `tg_gd_language_distribution` | `detected_language`, `post_count`, `pct_of_total` | Existing detected-language summary; not a validated LID output. |
| `tg_gd_hashtag_leaderboard` | `hashtag`, `post_count`, `channel_count`, `pct_of_hashtag_occurrences` | Hashtag prevalence. |
| `tg_gd_publication_timeline` | `published_month`, `post_count`, `distinct_channels` | Publication volume over time. |
| `tg_gd_ingestion_by_minute` | `scrape_minute`, `posts_scraped`, `channels_first_seen`, `comments_scraped` | Ingestion throughput and crawl timing. |
| `tg_gd_freshness_distribution` | `freshness_bucket`, `post_count`, `pct_of_total`, `avg_lag_hours` | Scrape/publication lag diagnostics. |
| `tg_gd_posts_per_channel_histogram` | `channel_bucket`, `channel_count`, `post_count`, `pct_of_channels`, `pct_of_posts` | Collection skew by channel. |
| `tg_gd_emoji_reaction_mix` | `emoji_name`, `total_reactions`, `posts_with_emoji`, `pct_of_all_reactions` | Reaction mix. |
| `tg_gd_emoji_reaction_by_language` | `emoji_name`, `detected_language`, `total_reactions`, `posts_with_emoji`, `pct_within_emoji`, `pct_within_language` | Reaction-language cross-tab. |
| `tg_gd_ad_vs_organic_by_channel` | `channel_id`, `channel_name`, `posts_total`, `posts_ad`, `posts_organic`, `posts_unknown`, `ad_pct` | Ad/organic labeling QA if `is_ad` is meaningful. |

## Sampling and Enrichment Tables

`sampling_history` appears in all three schemas with:

- `sampling_event_id`
- `platform`
- `ingest_id`
- `method`
- `sample_fraction`
- `random_seed`
- `input_row_count`
- `sampled_row_count`
- `languages_json`
- `sampled_languages_json`
- `started_at`
- `completed_at`
- `status`
- `notes`

`subsample_items` appears in all three schemas with item-level sampled content
and enrichment fields:

- Source identity: `subsample_id`, `sampling_event_id`, `source_table`,
  `source_record_id`, `source_channel_id`, `source_url`
- Content: `content_hash_sha256`, `content_lang_detected`,
  `content_length_chars`, `content_raw`, `translation_en_text`
- Enrichment: `toxicity_score`, `sentiment_label`, `sentiment_score`,
  `topic_top_k_json`, `ngrams_json`, `enrichments_json`
- Run provenance: `translator_run_id`, `enricher_run_id`,
  `translation_attempts`, `enrichment_attempts`
- Error tracking: `last_error_code`, `last_error_message`, `last_error_stage`
- Time/partition: `published_at`, `published_date`, `translated_at`,
  `created_at`, `updated_at`, `partition_date`

These are sampling/enrichment tables, not the primary population/sample-frame
tables for the TOO methodology.

## Embeddings

`post_embeddings` appears in `telegram_random_walk` and `telegram_too`.

Columns:

- `source_record_id`
- `platform`
- `embedding_1024`

Probe metadata:

- `telegram_random_walk.post_embeddings`: 0 files at probe time.
- `telegram_too.post_embeddings`: about 8.1 GB.

Use embeddings selectively for semantic clustering, topic validation, nearest
neighbor review, or duplicate/near-duplicate analysis. Do not make them a hard
dependency of the basic descriptive pipeline.

## Join Guidance

Recommended joins:

- Channels to channel metrics:
  - `tg_sl_channels.channel_id = tg_sl_channels_metrics.channel_id`
  - Include `ingest_id` or choose latest `scrape_timestamp` depending on the
    analysis.
- Posts to post metrics:
  - `tg_sl_posts.post_uid = tg_sl_posts_metrics.post_uid`
  - Cast `channel_id` as needed: posts use `bigint`; metrics use `string`.
  - Join on `ingest_id` or choose a latest metric snapshot if metrics are
    longitudinal.
- Posts to channels:
  - Cast `tg_sl_posts.channel_id` to string before joining to
    `tg_sl_channels.channel_id`.
- Comments to posts:
  - `tg_sl_comments.post_uid = tg_sl_posts.post_uid`
  - Also include `channel_id` where possible after casting.
- Comments to comment metrics:
  - `comment_id`, `post_uid`, `channel_id`, and optionally `ingest_id`.

Important pattern: metrics tables are time series. For a static channel or post
analysis frame, define a single metric snapshot policy, for example latest
`scrape_timestamp`, first observed, max observed, or a bounded analysis window.
Do not accidentally multiply rows by joining all metric snapshots to all entity
rows.

## Key Caveats for Analysis

1. `follower_count` is the likely Telegram subscriber/member metric, but its
   exact semantics must be confirmed for channels versus groups.
2. `views_count` in channel metrics and `post_view_count` in post metrics are
   distinct. Do not mix them without naming the estimand.
3. Post metrics and channel metrics are longitudinal. Build canonical latest
   snapshots explicitly.
4. `detected_language` exists in shaped tables and gold summaries, but this is
   not the planned validated LID v3 equivalent. Treat it as source/provisional
   language until validated.
5. Reaction data are represented differently by layer/schema: fixed structs,
   maps, and exploded `*_reactions` columns. Normalize before comparison.
6. `tg_sl_posts.channel_id` type differs from related tables. Cast explicitly.
7. The `tg_gd_*` tables are derived aggregates. Use them for QA and dashboard
   orientation, not as sole sources for denominator or model estimation.
8. No explicit random-walk chain, edge-list, validation-event, or exposure table
   was visible in the probed production schemas. The random-walk analysis plan
   needs derived tables or additional crawler logs.
9. `social_media_posts` in `telegram_random_walk` is a vector index/foreign
   table, not a normal row-level post table through Spark.
10. The older `prod_tads.telegram` bronze schema has somewhat different nested
   reaction and comment typing from `telegram_random_walk` and `telegram_too`.
   Prefer silver tables for cross-schema analysis.

## Mapping to the Planned Analysis

### Good Immediate Sources

- Channel frame:
  - `prod_tads.telegram_too.tg_sl_channels`
  - `prod_tads.telegram_too.tg_sl_channels_metrics`
- Message/post frame:
  - `prod_tads.telegram_too.tg_sl_posts`
  - `prod_tads.telegram_too.tg_sl_posts_metrics`
- Comment frame if needed:
  - `prod_tads.telegram_too.tg_sl_comments`
  - `prod_tads.telegram_too.tg_sl_comments_metrics`
- Quick dashboard QA:
  - `prod_tads.telegram_too.tg_gd_*`
- Random-walk raw source:
  - `prod_tads.telegram_random_walk.tg_bz_ingest`
  - `prod_tads.telegram_random_walk.tg_bz_ingest_log`

### Tables to Build for the Descriptive Project

The following planned analysis tables are not currently visible as clean
production surfaces and should be built in the new `telegram-descriptive`
project:

- `silver_channel_metric_snapshots`
  - One row per channel per selected metric snapshot policy.
- `silver_post_metric_snapshots`
  - One row per post per selected metric snapshot policy.
- `silver_telegram_edges`
  - Organic channel-to-channel edges from URLs, reposts, forwards, mentions,
    replies, and crawl parent-child fields where valid.
- `silver_random_walk_events`
  - One row per crawl event or discovered item, derived from crawler logs or
    `telegram_random_walk.tg_bz_ingest` if sufficient.
- `silver_random_walk_exposures`
  - Duplicate-collapsed eligible target exposures for Chao/saturation analysis.
- `silver_random_walk_validations`
  - Validation attempts and eligibility decisions for candidate Telegram
    channels/groups.
- `silver_ranked_metrics`
  - Ranked channel table by `follower_count`, `views_count`, and any approved
    post-view aggregation.
- `gold_channel_analysis_frame`
  - Joined channel, latest metrics, language, topic, sample-frame, and network
    features.
- `gold_message_analysis_frame`
  - Joined post/message text, metrics, language, content type, links, and
    channel covariates.
- `gold_population_estimates`
  - Chao/saturation count estimates, rank-tail denominators, and coverage
    estimates.
- `gold_too_sample_frame`
  - Final sample with denominator version, coverage scenario, and ingestion
    status.

## Suggested First Databricks QA Queries

Run these inside Databricks before implementing estimators:

```sql
select count(*) as rows, count(distinct channel_id) as channels
from prod_tads.telegram_too.tg_sl_channels;
```

```sql
select count(*) as rows, count(distinct post_uid) as posts, count(distinct channel_id) as channels
from prod_tads.telegram_too.tg_sl_posts;
```

```sql
select min(published_at), max(published_at), min(first_scrape_timestamp), max(last_scrape_timestamp)
from prod_tads.telegram_too.tg_sl_posts;
```

```sql
select count(*) as rows, count(distinct channel_id) as channels,
       min(follower_count), percentile_approx(follower_count, 0.5), max(follower_count)
from prod_tads.telegram_too.tg_sl_channels_metrics;
```

```sql
select count(*) as rows, count(distinct post_uid) as posts,
       min(post_view_count), percentile_approx(post_view_count, 0.5), max(post_view_count)
from prod_tads.telegram_too.tg_sl_posts_metrics;
```

```sql
select count(*) as rows, count(distinct id) as raw_nodes,
       count(distinct parentId) as parent_nodes
from prod_tads.telegram_random_walk.tg_bz_ingest;
```

Only run these after confirming cluster cost/latency expectations. For large
tables, prefer date-bounded or partition-bounded versions first.
