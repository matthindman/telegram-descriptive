# Telegram Descriptive Analysis Plan

Target home in the new repository: `docs/telegram_descriptive_analysis_plan.md`

This plan translates the YouTube descriptive analysis inventory, the Telegram
random-walk crawl methodology, and the rank-size tail-estimator notes into a
modular Telegram analysis project. The main design goal is to avoid one large
notebook that does everything. Notebooks should orchestrate and inspect; shared
code should implement reusable data contracts, estimators, plots, and exports.

It is grounded in a live metadata + light-profile probe of the actual Telegram
Databricks environment (`prod_tads.telegram*`, probed 2026-06-01; see
`scripts/telegram_databricks_resource_probe.py` and Section 4). The probe shows
the Telegram environment is materially richer than the YouTube-port inventory
assumed — silver channel/post/**comment** tables, exploded per-emoji reactions,
precomputed 1024-d post embeddings, `detected_language`, repost/reply/quote
linkage, hashtags, OCR/transcript text, and an already-enriched `subsample_items`
table all exist. The plan is sequenced to exploit those assets and to flag the
one pillar that is **not** well supported by current data: the random-walk crawl
lineage needed for population/coverage estimation (Section 4, "Gaps").

## 1. Project Objectives

The Telegram descriptive project should support four related outputs:

1. A defensible Telegram Top-of-the-Ocean sample frame: high-reach public
   Telegram channels/groups with quantified subscriber/member and, if selected,
   view coverage.
2. A descriptive analysis corpus: post/message-level and channel-level tables
   suitable for language, topic, content-type, engagement, and network analysis.
3. A methods package: diagnostics and tables documenting crawl behavior,
   eligibility, coverage, denominator estimation, uncertainty, and sensitivity.
4. A reusable research resource: stable gold tables and exports that allow
   later teams to compare their Telegram datasets to the discovered population
   and the TOO sample.

Non-goals for v1:

- Do not claim representativeness. The TOO is a high-reach curated sample with
  quantified coverage of a reachable public population, not a probability
  sample of all Telegram.
- Do not conflate random-walk discovery completeness with rank-size missing-mass
  estimation. They answer different questions and need separate diagnostics.
- Do not build one monolithic "core Telegram notebook." Split analyses by data
  contract and estimand.

## 2. Design Principles

- Thin notebooks, thick library code. Notebooks should load parameters, call
  tested functions, render diagnostics, and write outputs. Reusable logic should
  live in a package.
- Every stage has a table contract. Each analysis notebook should declare input
  tables, output tables, required columns, row grain, freshness assumptions, and
  known caveats.
- Durable outputs over notebook state. Important intermediate results should be
  written as versioned Delta tables or Parquet/CSV artifacts, not hidden in
  notebook variables.
- One row grain per table. Avoid tables that mix channel, message, edge, crawl
  event, and estimate rows. Use explicit keys and join surfaces.
- Configuration-driven thresholds. Crawl run IDs, language thresholds, topic
  taxonomy versions, rank boundaries, coverage targets, and bootstrap counts
  should be config values, not magic constants in notebooks.
- Reproducible estimator outputs. Estimation notebooks should write both the
  point estimates and the full parameter/diagnostic tables needed to reproduce
  a figure or methods table.
- Separate observed facts from inferred quantities. For example, observed member
  count, inferred denominator, sample coverage, and coverage lower confidence
  limit should be separate columns with clear provenance.
- Keep manual review loops explicit. LID validation, topic validation, and
  eligibility exceptions should write review queues and adjudication tables.

## 3. Suggested Repository Structure

```text
telegram-descriptive/
  README.md
  pyproject.toml
  databricks.yml
  docs/
    telegram_descriptive_analysis_plan.md
    data_contracts.md
    methods_tail_estimator.md
    methods_random_walk_crawl.md
    methods_language_detection.md
    methods_topic_classification.md
  src/
    telegram_descriptive/
      __init__.py
      config.py
      schemas.py
      io.py
      qc.py
      plotting.py
      tables.py
      crawl/
        contracts.py
        eligibility.py
        diagnostics.py
        exposure.py
        convergence.py
      estimation/
        chao.py
        saturation.py
        monotone_survival.py
        rank_tail.py
        bootstrap.py
        coverage.py
      language/
        segmentation.py
        inference.py
        aggregation.py
        validation.py
        adjudication.py
      topics/
        taxonomy.py
        prompts.py
        classification.py
        validation.py
      descriptive/
        frames.py
        concentration.py
        composition.py
        posting.py
        engagement.py
        robustness.py
      networks/
        links.py
        forwards.py
        communities.py
        missed_audience.py
      reporting/
        exports.py
        dashboards.py
        tables.py
  notebooks/
    00_data_inventory_and_contracts.py
    01_crawl_qa_and_walk_diagnostics.py
    02_discovery_population_estimation.py
    03_rank_tail_denominators.py
    04_too_sample_construction.py
    05_post_ingestion_audit.py
    06_language_detection.py
    06b_language_validation_and_adjudication.py
    07_topic_taxonomy_and_classification.py
    08_channel_message_analysis_frame.py
    09_audience_concentration_and_proxy_failure.py
    10_content_posting_and_engagement.py
    11_link_forwarding_networks.py
    12_missed_audience_sensitivity.py
    13_robustness_and_sensitivity.py
    14_reporting_exports.py
  jobs/
    databricks_workflows.yml
  tests/
    test_rank_tail.py
    test_chao.py
    test_coverage.py
    test_language_aggregation.py
    test_table_contracts.py
  validation/
    language_review_queues/
    topic_review_queues/
    eligibility_review_queues/
  outputs/
    figures/
    tables/
```

The exact folder names can change, but the separation should hold: crawl
diagnostics, population estimation, language, topics, descriptive frames,
networks, robustness, and reporting should not be one notebook.

## 4. Core Data Model

### Observed Databricks Sources

The lightweight Databricks inventory found three relevant production schemas:

- `prod_tads.telegram`: general/base Telegram collection surfaces.
- `prod_tads.telegram_random_walk`: random-walk collection surfaces. The visible
  bronze table contains random-walk-like fields, but clean walk-event,
  edge-list, validation, chain, and exposure tables were not visible in the
  probed schemas.
- `prod_tads.telegram_too`: Top-of-the-Ocean collection area and the best
  starting point for descriptive post/channel analysis.

For current table and column detail, see:

- `README_telegram_data_resources.md`
- `AGENT_TELEGRAM_DATA_CONTEXT.md`
- `databricks_telegram_resources.agent.json`

Core available surfaces:

- `tg_sl_channels`: shaped channel metadata.
- `tg_sl_channels_metrics`: channel metric time series with `follower_count`,
  `views_count`, `post_count`, `comment_count`, `like_count`, and
  `share_count`.
- `tg_sl_posts`: shaped post/message text, metadata, publication dates, links,
  hashtags, reply/repost fields, and provisional language fields.
- `tg_sl_posts_metrics`: post metric time series with `post_view_count`,
  `post_share_count`, `post_comment_count`, `post_like_count`,
  `total_emoji_reactions`, and individual `*_reactions` columns.
- `tg_sl_comments` and `tg_sl_comments_metrics`: comment text and comment
  metrics where available.
- `tg_gd_*` in `telegram_too`: derived gold dashboard aggregates for QA and
  orientation, not estimator source tables.

Observed aggregate scale from `telegram_too.tg_gd_collection_summary`:

- 29,099,371 posts across 1,662 channels.
- 177 provisional detected-language values.
- Scrape window from 2026-02-26 to 2026-03-04.
- Publication range from 2015-09-20 to 2026-03-04.
- `total_comments` is currently 0 in the gold summary, so comment analysis
  needs a separate coverage audit before it is treated as available.

Immediate data-model implications:

- Treat `follower_count` as the candidate member/subscriber metric, pending
  semantic confirmation.
- Treat `post_view_count` as the candidate post-level view metric and
  `views_count` as a separate channel-level metric. Do not mix them without an
  explicit estimand.
- Metrics tables are time series. The project needs explicit snapshot policies
  before joining metrics to entity frames.
- Cast channel IDs before joins: `tg_sl_posts.channel_id` appears as `bigint`,
  while channel and metric tables use `string`.
- The random-walk methodology still requires derived or external tables for
  crawl events, exposures, validation outcomes, edge lists, and chains.
- The corpus is extremely post-volume skewed: the `> 2000` posts/channel bucket
  accounts for about 98.8% of posts. Descriptive analysis must report
  channel-weighted and post-weighted summaries separately.
- Nearly one-quarter of posts are provisionally `NO TEXT`, and about 74.1% of
  posts are more than one year older than scrape time. Language, content, and
  current-attention analyses need no-text and recency-specific branches.

Additional source assets to exploit (present in the probe, not in the YouTube
pipeline) — these change the build order for several downstream notebooks:

- **`post_embeddings` (1024-d, in `telegram_random_walk`).** Precomputed post
  embeddings let topic work (notebook 07) start with unsupervised clustering to
  draft the taxonomy and seed labels *before* any LLM bake-off, and support
  cheap nearest-neighbor QA for both LID and topics. Confirm coverage/join key
  (`source_record_id` ↔ `post_uid`) in notebook 00.
- **`subsample_items` enrichments.** A sampled, already-enriched surface with
  `translation_en_text`, `toxicity_score`, `sentiment_label`/`score`,
  `topic_top_k_json`, `ngrams_json`, and `content_lang_detected`. Use it as (a) a
  labeled head start and stratification frame for LID/topic validation sampling
  (06b/07), and (b) a ready input for sentiment/toxicity descriptive cuts. Treat
  its labels as provisional until validated against the project's own taxonomy.
- **Post-level text is multi-source.** `post_content`, `all_text`,
  `searchable_text`, `image_text` (OCR), `transcript_text`, and `ocr_data` mean
  LID/topic segmentation (06/07) has far more signal than YouTube metadata —
  including media-only posts. Define per-source weights and a no-text fallback in
  `language/segmentation.py`.
- **Promotional axis is native.** `is_ad` / `ad_fields` on posts plus
  `tg_gd_ad_vs_organic_by_channel` give an ad-vs-organic split without bespoke
  spam heuristics; fold into content (10) and robustness (13).
- **Forward/reply/quote graph from real fields.** `repost_channel_data`,
  `shared_id`, `quoted_id`, `replied_id`, `root_post_id`, `is_reply`, `outlinks`,
  and `hashtags[]` are the edge sources for the networks notebook (11); they are
  distinct from (and richer than) the crawl `parentId`/`depth` lineage and must
  be kept separate from the crawl graph.
- **Channel-age proxy.** `tg_gd_channel_leaderboard.first_published` (earliest
  observed post) gives the age/incumbency signal YouTube lacked; use as a proxy
  with an explicit "first-observed, not founding" caveat.

### Bronze Inputs

These are close to source systems and should be minimally transformed.

- `bronze_telegram_ingest`
  - Observed source: `prod_tads.telegram_too.tg_bz_ingest` and
    `prod_tads.telegram_random_walk.tg_bz_ingest`.
  - Grain: raw or near-raw ingested Telegram post/message records.
  - Key columns: `post_uid`, `channel_id`, `channel_name`, `channel_data`,
    `all_text`, `searchable_text`, `description`, `image_text`,
    `transcript_text`, `comments`, `reactions`, `performance_scores`,
    `view_count`, `views_count`, `share_count`, `shares_count`, `file_name`,
    `file_path`, `ingest_id`, `ingestion_timestamp`, `scrape_timestamp`,
    `sourcing_status`, `failure_reason`, `published_date`.
- `bronze_random_walk_raw`
  - Observed source: `prod_tads.telegram_random_walk.tg_bz_ingest`.
  - Grain: raw random-walk ingested records.
  - Key columns in addition to standard Telegram ingest fields: `depth`,
    `error`, `id`, `messages`, `parentId`, `status`, `timestamp`.
  - Note: these fields may support derived crawl parentage, but they are not
    yet the clean walk-event/exposure tables needed for estimation.
- `bronze_crawl_walk_events`
  - Status: not visible as a clean production table in the probed schemas; must
    be derived from `telegram_random_walk` sources or supplied from crawler logs.
  - Grain: one crawl decision or transition event.
  - Key columns: `crawl_run_id`, `chain_id`, `step_id`, `timestamp`, `source`,
    `candidate_targets`, `followed_target`, `decision_type`, `restart_flag`,
    `walkback_flag`, `validator_status`.
- `bronze_scanned_messages`
  - Status: not visible as a separate clean production table; may be derivable
    from `tg_bz_ingest.messages`, `tg_sl_posts`, or external crawler logs.
  - Grain: one scanned message during mapping crawl.
  - Key columns: `crawl_run_id`, `source_channel_id`, `message_id`,
    `message_timestamp`, `text`, `urls_extracted`, `scan_status`.
- `bronze_validation_events`
  - Status: not visible as a separate clean production table; required for
    rigorous random-walk eligibility and exposure accounting.
  - Grain: one candidate Telegram handle/URL validation attempt.
  - Key columns: `candidate_url`, `normalized_username`, `validation_timestamp`,
    `search_public_chat_status`, `is_public`, `is_broadcast_or_supergroup`,
    `follower_count`, `title`, `about`, `failure_reason`.
- `bronze_channel_metadata_snapshots`
  - Observed source: `tg_sl_channels` plus `tg_sl_channels_metrics`.
  - Grain: one observed channel metadata snapshot.
  - Key columns: `canonical_channel_id`, `username`, `snapshot_timestamp`,
    `follower_count`, `channel_name`, `channel_url`, `public_status`,
    `channel_type`, `last_post_timestamp`, `source_run_id`.
- `bronze_messages_ingested`
  - Observed source: `tg_sl_posts` plus `tg_sl_posts_metrics`.
  - Grain: one ingested Telegram message/post after TOO selection.
  - Key columns: `canonical_channel_id`, `post_uid`, `published_at`,
    `post_content`, `all_text`, `searchable_text`, `post_type`,
    `post_view_count`, `post_share_count`, `total_emoji_reactions`,
    `reply_count`, `repost_channel_data`, `url`, `hashtags`.
- `bronze_seed_sources`
  - Status: not visible as a clean source table in the probed schemas.
  - Grain: one seed channel/source-list entry.
  - Key columns: `seed_id`, `canonical_channel_id`, `source_list`,
    `source_weight`, `draw_probability`, `seed_batch`, `eligibility_status`.

### Silver Canonical Tables

- `silver_channels`
  - One row per canonical Telegram channel/group.
  - Includes current best metadata, eligibility, latest `follower_count`,
    first/last observed timestamps, source provenance, and data-quality flags.
- `silver_channel_metric_snapshots`
  - One row per channel per selected metric snapshot policy.
  - Built from `tg_sl_channels_metrics`; stores latest/max/windowed
    `follower_count`, `views_count`, `post_count`, `comment_count`,
    `like_count`, and `share_count`.
- `silver_messages`
  - One row per ingested message/post.
  - Includes normalized text fields, content type, engagement counts, extracted
    entities, and ingestion quality flags.
- `silver_post_metric_snapshots`
  - One row per post per selected metric snapshot policy.
  - Built from `tg_sl_posts_metrics`; stores `post_view_count`,
    `post_share_count`, `post_comment_count`, `post_like_count`,
    `total_emoji_reactions`, and selected reaction families.
- `silver_edges`
  - One row per organic discovered Telegram edge.
  - Includes source, target, message ID if available, edge type
    (`url_link`, `forwarded_from`, `mention`, `hashtag_cooccurrence` if used),
    followed/skipped status, and artificial-edge exclusion flags.
- `silver_exposures`
  - One row per duplicate-collapsed eligible target exposure.
  - This is the base table for random-walk discovery estimation.
- `silver_ranked_metrics`
  - One row per channel per metric per ranking version.
  - Metrics include `follower_count`, `views_count`, and any approved post-view
    aggregation.
- `silver_lid_segments`
  - One row per channel/text segment used for language detection.
- `silver_topic_inputs`
  - One row per channel or message bundle submitted to topic classification.

### Gold Analysis Tables

- `gold_too_sample_frame`
  - Selected TOO channels with threshold, metric rank, coverage estimate,
    inclusion provenance, and post-ingestion status.
- `gold_channel_analysis_frame`
  - One row per channel with language, topic, member/view metrics, activity,
    content mix, network features, and source provenance.
- `gold_message_analysis_frame`
  - One row per ingested message with language, topic, content type, engagement,
    link/forward metadata, and channel covariates.
- `gold_population_estimates`
  - Crawl count estimates, Chao2 bounds, rank-tail denominators, bootstrap
    intervals, and coverage estimates by run/version/metric.
- `gold_validation_summaries`
  - LID validation, topic validation, eligibility validation, and table-quality
    checks.

## 5. Notebook and Module Plan

### 00 Data Inventory and Contracts

Purpose: establish what exists, what each table means, and whether the data are
fit for downstream analysis.

Inputs: Databricks catalog metadata, project config, and the observed
`prod_tads.telegram*` tables documented in `README_telegram_data_resources.md`.

Outputs:

- Table inventory with row counts, columns, null rates, min/max timestamps.
- Entity-grain audit for channel, message, edge, exposure, seed, and run tables.
- Canonical ID map and duplicate/conflict report.
- Data-resource markdown/JSON summary for researchers and future agents.
- Actual-source to planned-bronze/silver mapping.
- Gap list for missing crawler-log, validation, exposure, and seed tables.

Key checks:

- One canonical channel ID per username/history where possible.
- No silent mixing of channel-level and message-level rows.
- Timezone and timestamp semantics are explicit.
- Public/inaccessible/deleted/private statuses are retained, not dropped without
  a reason.
- `tg_sl_posts.channel_id` is cast safely before joins to channel/metric tables.
- Metric time-series join policies are explicit before any gold frames are
  created.

### 01 Crawl QA and Walk Diagnostics

Purpose: describe how the random-walk crawl behaved before making population
claims.

Inputs: visible random-walk sources
`prod_tads.telegram_random_walk.tg_bz_ingest` and
`prod_tads.telegram_random_walk.tg_bz_ingest_log`, plus any external crawler
logs that contain chain IDs, validation events, candidate targets, restarts,
walkbacks, and exposure decisions.

Outputs:

- Derived `silver_random_walk_events` if enough source fields exist.
- Derived `silver_random_walk_edges` or an explicit gap report if source fields
  are insufficient.
- Derived `silver_random_walk_validations` or an explicit gap report.
- Walk transition summary by chain and run.
- Restart/walkback/forced-walkback rates.
- Candidate extraction and validation funnel.
- Dead-end, stale-channel, no-message, below-threshold, and invalid-target
  rates.
- Seed coverage and seed-draw diagnostics.
- Per-chain exposure and discovery timelines.

Key analyses:

- Audit whether `depth`, `id`, `parentId`, `status`, `timestamp`, `messages`,
  and `error` can reconstruct walk parentage and step state.
- Confirm whether `parentId` represents crawl parentage, Telegram reply
  parentage, source-system parentage, or some other relationship before using
  it as a crawl edge.
- Step-mix plots over crawl time.
- Chain-level depth, step count, unique source count, unique target count.
- Validation latency and failure modes.
- Followed-vs-skipped target comparisons.
- Duplicate URL/handle exposure rates.
- Distribution of member counts for seeds, visited channels, validated targets,
  and followed targets.

### 02 Discovery Population Estimation

Purpose: estimate discovery/count completeness for the reachable public
population under the crawl design.

Inputs: `silver_random_walk_exposures`, crawl chains, validated channel
metadata, and latest `follower_count` snapshots. If these tables cannot be
derived from the visible `telegram_random_walk` schema, this notebook should
stop with a gap report rather than manufacturing population estimates.

Outputs:

- Post-burn-in accumulation curves by threshold `K`.
- Chao2 lower bounds using chains as replicated samples.
- Simple and stretched-exponential random-walk saturation fits to binned
  discovery increments.
- Monotone threshold survival estimates `N>=K`.
- Burn-in and convergence diagnostics.

Key analyses:

- Define burn-in using log member counts of discoveries, discovery rate per
  exposure bin, step mix, and chain diagnostics.
- Equalize chains to common post-burn-in exposure before comparing incidence.
- Compute observed discoveries, singleton-across-chain counts, doubletons,
  Chao2 lower bounds, and uncertainty.
- Fit saturation models to discovery increments, with held-out predictive
  checks.
- Enforce nonincreasing `N>=K` across thresholds with isotonic adjustment and
  Chao floors.
- Report cross-chain consistency and Rhat-style heuristics.

Important separation:

- This notebook estimates channel-count discovery completeness.
- It does not estimate total audience mass by itself. Audience mass denominators
  are handled in notebook 03 using the rank-size tail estimator.

### 03 Rank-Tail Denominators

Purpose: estimate unobserved member/view mass below a trusted observed head.

Inputs: `silver_ranked_metrics`, head-closure evidence from notebook 02,
candidate metric definitions, and metric snapshots derived from
`tg_sl_channels_metrics` and `tg_sl_posts_metrics`.

Outputs:

- Ranked metric tables for `follower_count`, `views_count`, and selected
  post-view aggregation.
- Candidate boundary grid `r_c`.
- Tail-estimator parameter table: `r_c`, `y0`, `alpha0`, `eta0`, `eta1`,
  `eta2`, fitting-window size, boundary diagnostics.
- D0-D3 tail mass and total mass estimates.
- Boundary-sensitivity and model-ladder coverage tables.
- Diagnostic log-log plots and derivative plots.

Estimator plan:

- Build a deduplicated ranked table per metric. Use `follower_count` as the
  candidate member/subscriber metric, pending semantic confirmation.
- Choose candidate trusted-head boundaries using crawl closure, source overlap,
  and recent high-rank discovery diagnostics.
- Estimate `y0` with a narrow local-linear smoother around `r_c`.
- Estimate `alpha0` and `eta0` with tricube-weighted local quadratic fits on
  `log(metric)` vs `log(rank)`.
- Estimate `eta1` and `eta2` from staggered local quadratics.
- Resolve and document the finite-difference formula before implementation,
  because the current explainer and attached code differ.
- Fit four nested models:
  - D0: constant `alpha`, pure power law.
  - D1: constant `eta`, steepening slope.
  - D2: accelerating steepening.
  - D3: one further derivative.
- Integrate the continuous tail; use finite-support or discrete variants when
  a credible `R_max` exists.

Key diagnostics:

- Concavity of log-log rank-size curve near the boundary.
- `alpha0 > 1` for finite D0 tail mass.
- Stability of `eta0` across plausible boundaries.
- D0 >= D1 >= D2 >= D3 under nonnegative shape constraints.
- Boundary grid sensitivity.
- Applicability failure flags: too few ranks, convex curve, unstable derivative
  estimates, no trusted head, metric censoring.

### 04 TOO Sample Construction

Purpose: choose and document the v1 high-reach Telegram sample.

Inputs: denominators from notebook 03, candidate channel metrics, eligibility
table, observed `telegram_too` channel/post tables, and post-ingestion status
if available.

Outputs:

- Candidate samples by member threshold, view threshold, top-N, and combined
  criteria.
- Coverage estimates under D0-D3 denominators.
- Conservative lower-coverage scenario and preferred committee option.
- Sample membership churn across thresholds.
- Final `gold_too_sample_frame`.

Key analyses:

- Rank correlation between `follower_count`, `views_count`, and
  `post_view_count` aggregates.
- Lorenz/Gini/top-k concentration for members and views.
- Subscriber/member-vs-view superlinearity.
- Coverage-vs-threshold curves.
- Committee options table with sample size, numerator mass, denominator
  scenario, lower confidence limit, and caveats.
- Non-representativeness warning and denominator versioning.

Decision points:

- v1 metric: members/subscribers, views, or both.
- Coverage target and tolerance.
- Whether headline denominator uses D0 conservative estimate or a justified
  curvature-corrected estimate.

### 05 Post-Ingestion Audit

Purpose: verify that selected TOO channels actually have usable message-level
data.

Inputs: final TOO frame,
`prod_tads.telegram_too.tg_sl_posts`,
`prod_tads.telegram_too.tg_sl_posts_metrics`,
`prod_tads.telegram_too.tg_sl_channels`, and
`prod_tads.telegram_too.tg_sl_channels_metrics`.

Outputs:

- Ingestion success/failure report by selected channel.
- Message coverage by date range.
- Missing/deleted/inaccessible channel report.
- Content and engagement field completeness.
- Final post-ingestion inclusion/exclusion flags.

Key analyses:

- Expected vs observed selected channels.
- Earliest/latest post timestamp by channel.
- Message count by channel and month.
- View/reaction/forward field availability.
- Auto-delete or retention-window indicators where observable.
- Channels selected for TOO but absent from message corpus.

### 06 Language Detection

Purpose: produce channel-level and message-level language labels comparable to
the YouTube LID v3 workflow, but adapted to Telegram text.

Inputs: `silver_messages`, `silver_channels`, `tg_sl_posts` text fields,
`tg_sl_channels` metadata, existing provisional `detected_language`, and
optional OCR/ASR if later added.

Outputs:

- Segment-level LID predictions.
- Channel-level language aggregation.
- Message-level dominant language where needed.
- Ambiguous/mixed/no-text labels.
- LID diagnostics and review queues.

Segmentation:

- Channel title.
- Channel about/description.
- Recent message text sample.
- High-engagement message sample.
- Link-preview text if retained and reliable.
- Optional separated samples for forwarded text vs original channel text.

Aggregation:

- Keep per-segment evidence.
- Weight metadata and message text separately.
- Avoid over-weighting duplicated forwards or boilerplate.
- Preserve multilingual/mixed-channel status rather than forcing a single label
  when evidence is genuinely mixed.

Diagnostics:

- Label distributions overall and by member/view cohort.
- High-risk tail labels and confusable languages.
- Script mismatch and romanization traps.
- No-text/media-heavy channel rates.
- Language coverage by source list and crawl route.

### 06b Language Validation and Adjudication

Purpose: validate LID, calibrate confidence, and create a gold review set.

Inputs: LID predictions, stratified review samples, manual/LLM adjudication.

Outputs:

- Validation sample.
- Per-language precision/recall where feasible.
- Disagreement queue.
- Adjudicated label table.
- Acceptance thresholds for downstream use.

Validation cohorts:

- Top member channels.
- Top view channels.
- High-impact languages.
- Confusable language families.
- Mixed-language channels.
- No-text or low-text channels.
- Source-list-specific samples.

### 07 Topic Taxonomy and Classification

Purpose: define and apply Telegram-native channel topics.

Inputs: channel metadata, message samples, language labels, candidate taxonomy,
LLM outputs, manual review.

Outputs:

- Taxonomy version.
- Prompt/version metadata.
- Channel-level topic predictions.
- Topic confidence/evidence table.
- Validation and adjudication tables.

Taxonomy design:

- Start from YouTube channel-topic ideas but do not copy categories blindly.
- Include Telegram-specific categories likely to matter: news/politics,
  geopolitics/war, health, crypto/finance, commerce, entertainment, religion,
  ideology/movements, scams/spam, file sharing, adult content if applicable,
  local community, education, and mixed/unknown.
- Decide whether topics are single-label, multi-label, or hierarchical.
- Include an explicit "channel function" axis if useful: broadcaster, aggregator,
  discussion group, mirror, bot/admin utility, marketplace, link farm.

Classification:

- Use evidence bundles: title, about, representative messages, top-viewed
  messages, URLs/domains, forwarded-from sources.
- Avoid sending huge message histories to LLMs.
- Track prompt version, taxonomy version, model, temperature, evidence IDs.
- Generate review queues for low confidence, high reach, and contested topics.

### 08 Channel and Message Analysis Frame

Purpose: create the main reusable gold frames for descriptive notebooks.

Inputs: channel metadata, message data, LID labels, topic labels, TOO sample,
coverage estimates, ingestion audit.

Outputs:

- `gold_channel_analysis_frame`.
- `gold_message_analysis_frame`.
- Frame QA report.

Channel frame columns:

- IDs and usernames.
- Eligibility and public status.
- TOO inclusion and threshold status.
- Member count, view metrics, rank metrics.
- Language label and confidence.
- Topic label(s) and confidence.
- Activity metrics.
- Content-type shares.
- Link/forward/network metrics.
- Source provenance and crawl-discovery path.

Message frame columns:

- Channel ID and message ID.
- Timestamp and date parts.
- Text length and normalized text indicators.
- Media/content type.
- Views, reactions, forwards, replies.
- Language prediction if message-level LID is run.
- URLs/domains/mentions/hashtags.
- Forwarded-from metadata.
- Topic if message-level topics are later needed.

### 09 Audience, Concentration, and Proxy Failure

Purpose: reproduce and adapt the core YouTube attention analyses for Telegram.

Inputs: gold frames, denominators, TOO sample frame.

Outputs:

- Concentration tables and figures.
- Member/view proxy-failure analysis.
- Coverage-aware attention summaries.
- Language/topic market share tables.

Key analyses:

- Distribution of member count, views, posts, engagement.
- Top-k shares by members and views.
- Lorenz curves, Gini, HHI, and concentration ratios.
- Rank correlation and divergence between member count and views.
- Channels with high member count but low views, and high views but lower
  member count.
- Coverage-adjusted top-share estimates using D0-D3 denominators.
- Concentration by language and topic.
- Sensitivity to excluding inaccessible or low-data channels.

### 10 Content, Posting, and Engagement

Purpose: describe what the TOO channels post and how audiences engage.

Inputs: `gold_message_analysis_frame`, channel frame.

Outputs:

- Posting frequency and recency tables.
- Content-type composition.
- Engagement distributions.
- Temporal activity summaries.

Key analyses:

- Posts per day/week/month by channel.
- Active/inactive/stale channel status.
- Text/image/video/document/link/poll/audio/sticker shares.
- Original vs forwarded content share.
- View distributions by content type.
- Reactions, forwards, replies per view where fields exist.
- Burstiness and event-window responsiveness if dates are central.
- Retention/deletion caveats for views and message availability.

### 11 Link and Forwarding Networks

Purpose: analyze Telegram-native network structure beyond the crawl graph.

Inputs: messages, URLs, forwards, mentions, edge tables, channel frame.

Outputs:

- Directed link graph.
- Forwarding graph.
- Domain/link summary.
- Community and centrality summaries.

Key analyses:

- Channel-to-channel URL links.
- Forwarded-from relationships.
- Mention networks.
- Outbound domains and platform links.
- Central channels by in-degree, out-degree, PageRank, and betweenness if
  graph size permits.
- Topic/language mixing in networks.
- Link farms, mirrors, and repeated cross-post clusters.

Important distinction:

- Keep the organic network graph separate from the crawl transition graph.
- Exclude artificial restarts and walkbacks from community detection.

### 12 Missed-Audience Sensitivity

Purpose: assess the risk that the crawl missed high-audience basins.

Inputs: organic edge graph, crawl paths, chain IDs, first-discovery metadata,
member/view metrics.

Outputs:

- Stable crawl-discovery clusters.
- Cluster stability and audience-recovery tables.
- Dark-audience omission sensitivity tables.
- Missed-audience methods appendix outputs.

Key analyses:

- Build graph from followed and skipped organic links.
- Symmetrize and hub-deweight for community detection.
- Preserve directed timestamped inference graph separately.
- Run multi-resolution community detection and consensus clustering.
- Bootstrap whole chains, rebuild clusters, and assess stability.
- Compute audience-weighted Jaccard, dissolution, leakage, and PAC.
- Record first-discovery parentage and dependency basins.
- Estimate seed-entry intensity and outside-link entry intensity.
- Compute dark-audience omission bounds for `kappa = 1, 10, 30, 100, infinity`.
- Run partial-discovery diagnostics within stable observed clusters.

### 13 Robustness and Sensitivity

Purpose: centralize robustness checks instead of scattering them across every
notebook.

Inputs: outputs from notebooks 02-12.

Outputs:

- Robustness matrix.
- Sensitivity appendix tables.
- Reviewer-check summary.

Checks:

- Different burn-in definitions.
- Different exposure bin sizes.
- Different Chao/saturation threshold grids.
- Different rank-tail boundaries `r_c`.
- D0-D3 denominator scenarios.
- Member-only, view-only, and combined sample cuts.
- Excluding low-confidence LID/topic labels.
- Excluding deleted/inaccessible/stale channels.
- Source-list-only vs crawl-discovered channels.
- Public broadcast channels vs supergroups.
- Alternative content-type mappings.
- Bootstrap interval method sensitivity.

### 14 Reporting Exports

Purpose: produce clean research artifacts from stable gold tables.

Inputs: gold tables and robustness summaries.

Outputs:

- Methods tables.
- Main descriptive figures.
- Appendix figures.
- Versioned CSV/Parquet exports.
- Data dictionary.
- Public/internal denominator package.

Exports:

- TOO sample frame.
- Channel-level analysis frame.
- Message-level analysis frame if approved.
- Population and coverage estimates.
- Language and topic summary tables.
- Network summary tables.
- Validation summaries.

## 6. Databricks Workflow Shape

Recommended job groups:

1. Data contracts and canonicalization.
2. Crawl QA and discovery estimation.
3. Rank-tail denominators and TOO sample construction.
4. Post-ingestion audit.
5. Language pipeline.
6. Topic pipeline.
7. Gold frame build.
8. Descriptive analysis notebooks.
9. Robustness and reporting.

Each workflow should write a run manifest with:

- Git commit SHA.
- Config version.
- Input table versions.
- Output table names/versions.
- Run start/end time.
- Row counts.
- Known warnings.

## 7. Testing and QA Plan

Unit tests:

- Rank-tail D0 closed form and D0 >= D1 >= D2 >= D3 under nonnegative
  curvature.
- Chao2 calculations on toy incidence matrices.
- Exposure duplicate-collapsing.
- Coverage calculations under denominator scenarios.
- Language channel aggregation from segment predictions.
- Topic taxonomy validation helpers.
- Table schema validation.

Notebook smoke tests:

- Each notebook should be runnable on a tiny fixture dataset.
- Each notebook should fail early if required tables/columns are absent.
- Each notebook should produce at least one small QA summary table.

Data QA:

- Row-count deltas across versions.
- Null-rate thresholds for critical fields.
- Duplicate key checks.
- Metric nonnegativity checks.
- Timestamp range checks.
- Eligibility flag consistency.
- Gold frame one-row-per-key checks.

## 8. Milestone Sequence

### Milestone 1: Data Contracts and Crawl QA

Deliverables:

- Data inventory.
- Canonical channel/message/edge/exposure tables.
- Crawl QA dashboard.
- Seed and validation funnel diagnostics.

Exit criteria:

- The team agrees on row grains, canonical IDs, eligibility rules, and source
  table meanings.

### Milestone 2: Population and Denominator Estimation

Deliverables:

- Burn-in and convergence diagnostics.
- Chao2/saturation discovery estimates.
- Rank-tail denominator estimates.
- Coverage denominator scenarios.

Exit criteria:

- The team can explain what population the TOO covers and how denominator
  uncertainty enters coverage claims.

### Milestone 3: TOO Sample and Ingestion Audit

Deliverables:

- Candidate sample options.
- Final v1 sample frame.
- Post-ingestion audit.
- Non-representativeness and coverage caveats.

Exit criteria:

- There is a stable list of channels for downstream descriptive analysis.

### Milestone 4: Language and Topic Labels

Deliverables:

- Telegram LID predictions and validation.
- Telegram topic taxonomy and classifier outputs.
- Review/adjudication tables for high-impact uncertain cases.

Exit criteria:

- Labels are good enough for aggregate descriptive analysis, with known failure
  modes documented.

### Milestone 5: Core Descriptive Analysis

Deliverables:

- Channel/message analysis frames.
- Concentration and proxy-failure analysis.
- Content/posting/engagement analysis.
- Link/forwarding/network analysis.

Exit criteria:

- Main descriptive tables and figures can be generated from gold tables without
  rebuilding upstream estimators.

### Milestone 6: Robustness and Release Package

Deliverables:

- Robustness appendix.
- Missed-audience sensitivity.
- Final report exports.
- Data dictionaries and methods notes.

Exit criteria:

- A reader can trace every headline estimate to input tables, config, estimator
  version, and sensitivity checks.

## 9. Immediate Implementation Tasks

1. Create the repo skeleton and package modules.
2. Copy `README_telegram_data_resources.md`,
   `AGENT_TELEGRAM_DATA_CONTEXT.md`, and
   `databricks_telegram_resources.agent.json` into the new repo's `docs/` or
   `src/` context area.
3. Write `docs/data_contracts.md` with mappings from actual Databricks tables
   to planned bronze/silver/gold tables.
4. Implement schema validators before analysis notebooks grow, including
   explicit checks for `channel_id` type mismatches and metric snapshot
   multiplicity.
5. Port only the reusable parts of YouTube LID/topic/descriptive logic; do not
   copy the notebook structure wholesale.
6. Build `silver_channel_metric_snapshots` and `silver_post_metric_snapshots`
   from `tg_sl_*_metrics`.
7. Audit whether `telegram_random_walk.tg_bz_ingest` plus crawler logs can
   produce clean walk events, validation events, edge lists, chains, and
   exposure tables.
8. Implement crawl QA before population estimation.
9. Implement random-walk discovery estimation before making coverage claims.
10. Implement the rank-tail estimator as a tested module before using it in a
   notebook.
11. Build the TOO sample construction notebook only after denominators are
   versioned.
12. Build language and topic validation queues early, because adjudication will
   create scheduling drag.
13. Keep final descriptive notebooks downstream of stable gold frames.

## 10. Key Open Decisions

- What exact Telegram population is in scope: public broadcast channels only,
  public supergroups, or both?
- Does `follower_count` mean Telegram channel subscribers, group members, or a
  source-system follower abstraction across both?
- What is the v1 audience metric: `follower_count`, views, or both?
- If using views, what view definition is reliable enough: retained-message
  views via `post_view_count`, recent-message views, channel-level
  `views_count`, or a modeled measure?
- Can `telegram_random_walk.tg_bz_ingest` fields such as `depth`, `id`,
  `parentId`, `status`, `messages`, and `timestamp` reconstruct crawl chains
  and exposures, or do we need separate crawler logs?
- What coverage target and lower-confidence rule should define sample readiness?
- Which rank-tail denominator should be headline: conservative D0, preferred
  curvature-corrected D1/D2/D3, or a range?
- What topic taxonomy granularity is useful without creating unreliable
  fine-grained labels?
- Which Telegram-specific high-risk categories require special validation?
- What parts of the discovered channel list can be released, and what must stay
  internal?
