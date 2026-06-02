# YouTube Analysis Inventory for a Telegram Port - Revised

Purpose: consolidate two inventories of the YouTube analysis code into a
Telegram planning document. This version keeps the stronger detailed structure
from `ANALYSIS_INVENTORY_for_telegram_port.md`, adds items missed in my first
pass, and adds two surfaces the other inventory underweighted:

- the parallel Codex attention notebook diagnostics;
- the documented existing YouTube data-resource / gold aggregate surfaces.

Portability tags:

- `[PORT]` Corpus-agnostic method; likely carries to Telegram with field-name
  changes.
- `[REMAP]` Method carries, but the field set, weights, or taxonomy must be
  redesigned for Telegram.
- `[YT-ONLY]` Depends on a YouTube-only signal; drop or replace with a
  Telegram-native substitute.
- `[ADD]` Not in the YouTube code, but likely needed for Telegram.

Working translation: YouTube channel -> Telegram channel/group; YouTube video
-> Telegram message/post; YouTube subscriber -> Telegram member/subscriber
count where available.

## Comparison Notes

What my first answer missed or compressed too much:

- It was too high-level for Notebook 01. I missed many concrete LID analyses:
  deterministic dedup and smoke sampling, resumable hash buckets, script
  metrics, text-validity thresholds, segment-universe parity, per-model vote
  tables, exact consensus statuses, mixed-language screen vs credible logic,
  Hindi/Indic recall diagnostics, high-risk tail-label diagnostics, validation
  strata, ablation summaries, and acceptance checks.
- It under-described Notebook 02. The category workflow is not just "topic
  classification"; it includes reference-label normalization, video-to-channel
  label aggregation, language-stratified sampling, provider batch generation,
  parse-error tracking, macro-F1 on a full class grid, pairwise model agreement,
  and a decision gate before full-corpus inference.
- It under-described Notebook 03. The LLM language panel has explicit routing
  rules, blind agreement audits, provider-neutral parsing, majority-vote
  reconciliation, provenance tagging, and a one-verdict-per-routed-channel
  assertion.
- It compressed Notebook 10. The attention notebook includes snapshot
  completeness checks, entry/exit status, traffic blocks, threshold capture,
  Lorenz/Gini/top-k concentration, language/category composition, JSD, proxy
  failure, age/language-population analysis, production/format analysis, and a
  robustness battery.

What the other model did better:

- It produced a proper porting inventory rather than a short executive
  summary.
- It tagged each item by portability, which is exactly the useful structure for
  Telegram planning.
- It captured many implementation details that matter for parity: field
  weights, thresholds, output tables, sample strata, provider batch plumbing,
  and evaluation metrics.

What the other model missed or overstated:

- It treated the five source notebooks as the whole universe. There is also a
  parallel Codex attention notebook with useful diagnostics and an explicit
  source-data manifest pattern.
- It did not include the data-resource map / existing gold aggregate surfaces
  documented in `README_data_resources.md`.
- It was a little optimistic that subscriber/member cohorts port directly.
  Telegram member counts may be missing, stale, private, or non-comparable
  across groups/channels, so this should be `[REMAP]` unless coverage is known.
- It called `source_language_confusion` YouTube-only. That is true for
  YouTube's declared language fields, but Telegram could have analogues if the
  collection pipeline has collector-provided locale, channel metadata language,
  country, UI language, or source-list labels.

## 1. Language Detection - Notebook 01, LID v3

Source: `01_language_openlid_v3_databricks.py`

Measures dominant written-metadata language at the channel level, not spoken
language. It classifies text segments separately, aggregates to channel-level
labels, compares OpenLID-v3 and GlotLID, and emits model-specific and consensus
outputs.

### Source Prep and Segmentation

- `[PORT]` Deterministic channel/video deduplication. Uses ordered
  `row_number()` with timestamp, row hash, and key tie-breaks rather than
  unordered `dropDuplicates()`. Outputs dedup/count QA.
- `[PORT]` Deterministic smoke sampling. Samples by stable hash order, not
  Spark partition order.
- `[PORT]` Resumable bucketed production runs. Uses `run_id`,
  `channel_hash_bucket`, bucket ranges, and Delta `replaceWhere` to retry
  partial runs without mixing old/new outputs.
- `[REMAP]` Recent-N content cap. YouTube defaults to recent videos per
  channel; Telegram should use recent messages/posts per channel, and may need
  time-window caps for high-volume channels.
- `[REMAP]` Canonical segment table `yt_lid_v3_segments_input`. YouTube
  segment types are `channel_name`, `channel_description`, `video_title`,
  `video_description`, and `video_tags`. Telegram should remap to channel/group
  title, handle, bio/about, message text, media captions, pinned messages, and
  perhaps forwarded/original text.
- `[PORT]` Text cleaning and per-script metrics. Counts Unicode letters by
  script, dominant script, dominant-script share, URL/hashtag/emoji flags, and
  clean-letter counts.
- `[PORT]` Text-validity rule. A segment is valid if it has enough clean letters
  or a non-Latin dominant-script exception. Telegram should keep the rule, then
  recalibrate thresholds after inspecting message lengths.

### Model Inference

- `[PORT]` OpenLID-v3 fastText inference over valid segments.
- `[PORT]` GlotLID fastText inference over the same valid segment universe.
- `[PORT]` Optional GlotLID native-preprocessing audit. Useful for model-method
  audits but kept separate from the main comparison.
- `[PORT]` Optional low-confidence-only GlotLID audit mode. Useful as a runtime
  fallback, but not valid for population agreement rates.
- `[PORT]` Label normalization from raw fastText labels into language label,
  ISO-639-3 base, and script.
- `[PORT]` Segment-universe parity checks. Confirms the two models ran on the
  same segment set, including count and checksum parity.

### Per-Model Channel Aggregation

- `[REMAP]` Weighted segment voting. YouTube weights are currently shaped around
  video metadata: `video_title=2.0`, `channel_description=1.0`,
  `video_description=1.0`, `video_tags=0.5`, `channel_name=0.25`. Telegram needs
  new weights for channel title, bio, post text, captions, pinned messages, and
  forwarded text.
- `[PORT]` Top-k vote admission. Top-1 and admitted top-2 predictions
  contribute to language votes under score/ratio thresholds.
- `[PORT]` Per-channel language vote table. Outputs weighted votes by channel,
  model, and language.
- `[PORT]` Per-model channel summary. Outputs primary/secondary language,
  vote-share confidence proxy, segment counts, score summaries, and vote JSON.

### Model Comparison and Consensus

- `[PORT]` Segment-level OpenLID-vs-GlotLID comparison: exact, ISO, script, and
  cluster agreement.
- `[PORT]` Channel-level model comparison: primary/secondary agreement, model
  confidence, high-risk flags, and consensus inputs.
- `[PORT]` Analysis clusters for near-language/taxonomy cases, including
  Arabic-family normalization, Chinese script variants, Malay/Indonesian,
  Hindi-family languages, Romance tail labels, and other clusters.
- `[PORT]` Deterministic consensus classifier. Emits `consensus_status`,
  `consensus_language_label`, `consensus_for_rollup_label`,
  `consensus_source`, and `requires_manual_adjudication`.
- `[PORT]` Agreement summaries by exact label, ISO, cluster, and script.

### Specialized LID Diagnostics

- `[PORT]` Mixed-language detection. Separates permissive "screen" from stricter
  "credible candidate"; requires evidence such as vote share, segment count,
  top-1 support, segment-type diversity, rank margins, cross-script evidence,
  and second-model support.
- `[REMAP]` Hindi/Indic recall diagnostics. The framework ports as a
  family-specific recall audit; the keyword lists and target families should be
  chosen after Telegram residual validation.
- `[PORT]` High-risk tail-label diagnostic. Flags labels such as rare
  Romance/minority languages that fastText models may hallucinate for major
  Latin-script content.
- `[REMAP]` Source-language confusion. YouTube compares model output to declared
  YouTube language fields. Telegram can only reproduce this if there is an
  analogous collector/source-list metadata field.
- `[PORT]` Unclassified audit. Surfaces sparse-text, invalid-text, and
  insufficient-text channels.

### Validation, Ablation, Acceptance

- `[PORT]` Final channel table: one row per channel with per-model,
  consensus, mixed-language, Hindi/Indic, high-risk, and status fields.
- `[YT-ONLY]` Optional write-back into `yt_sl_channels.detected_language`.
  Telegram should keep predictions in separate tables until validation is
  complete.
- `[PORT]` Summary tables: exact language summary, rollup summary, model
  agreement summary, suspect-tail sample, unclassified audit.
- `[PORT]` Manual validation sample. Deterministic stratified sample across
  high-confidence, low-confidence, mixed, high-risk, Hindi/Indic, source
  disagreement, exact/cluster disagreement, insufficient text, and non-Latin
  controls.
- `[PORT]` Ablation analysis. Re-aggregates stored segment predictions under
  alternative weights, top-2 settings, thresholds, and rollups; reports label
  churn against default OpenLID and default consensus without rerunning
  inference.
- `[PORT]` Acceptance checks. Verifies config criteria, required output tables,
  one-row-per-channel invariants, and current-run metadata.

## 2. Subscriber-Cohort LID Driver - Notebook 01b

Source: `01b_language_lid_v3_subscriber_cohort_analysis_databricks.py`

Builds subscriber-based evaluation cohorts, runs Notebook 01 for each cohort,
and compares language outcomes across high-subscriber and random-band channels.

- `[REMAP]` Subscriber/member parsing and deterministic deduplication. The
  method ports, but Telegram member counts may be unavailable, hidden, stale, or
  collected with different semantics.
- `[REMAP]` Top-size cohort. YouTube uses top 100k subscriber channels and
  records the cutoff and tie counts. Telegram should choose an equivalent
  member/view/activity cohort after checking coverage.
- `[REMAP]` Random size-band cohort. YouTube samples from channels below the
  top cutoff and above a lower subscriber threshold. Telegram should use member
  count, recent view volume, activity, or another exposure proxy.
- `[PORT]` Cohort ID tables and cutoff metadata.
- `[PORT]` Cohort source table materialization before child notebook runs.
- `[PORT]` Twin child LID runs with distinct `run_id`s and separate output table
  families.
- `[PORT]` Combined channel-level language results with cohort membership,
  selection rank, size metrics, and LID outputs.
- `[PORT]` Cohort status summary, consensus-language summary, review queue, and
  model-agreement-by-cohort outputs.

## 3. LLM Language-Adjudication Panel - Notebook 03

Source: `03_language_llm_panel_databricks.py`

Routes only contested or audit channels to a three-LLM language panel. It is a
targeted adjudication layer, not a full-population classifier.

- `[PORT]` Three-provider independent panel. Defaults to OpenAI, Anthropic, and
  Gemini frontier models.
- `[REMAP]` Batch-adapted classifier prompt. The guardrails port: written
  metadata only, Latin-name trap, romanization, English/creole distinction,
  rare-tail conservatism, Arabic/Mandarin/Indonesian normalization,
  mixed-language handling, and abstention. The supplied metadata fields must be
  remapped for Telegram.
- `[PORT]` Disagreement routing. Sends fastText disagreement, fallback, and
  missing/error cases to the panel.
- `[PORT]` Unresolved high-risk-tail routing. Sends tail cases with no safe
  consensus label.
- `[REMAP]` Shared-bias route. YouTube has an English-with-Indic-evidence route.
  Telegram should generalize this to "models agree on X but strong script,
  keyword, or source-list evidence suggests Y."
- `[PORT]` Blind agreement-bucket audit. Samples a small deterministic slice of
  settled fastText labels to estimate residual error.
- `[REMAP]` Prompt builder. Includes all segment rows, including fastText-invalid
  short segments as weak evidence. Telegram should include short titles/handles
  and short posts carefully, with caps.
- `[PORT]` Provider-specific JSONL batch generation and optional submission.
- `[PORT]` Provider-neutral result parsing and validation.
- `[PORT]` Majority-vote reconciliation on base ISO, preserving full winning
  label/script and side fields.
- `[PORT]` Per-provider reach and label breakdown.
- `[PORT]` Consensus provenance tagging: `llm_panel`, `human_review`, and
  `audit_sample`; audit rows are measurements, not automatic overwrites.
- `[PORT]` Coverage assertion: exactly one verdict row per routed channel.
- `[PORT]` Agreement-bucket audit readout: panel-vs-fastText disagreement rate
  among "confident" cases.

## 4. Channel Topic / Category Classification - Notebook 02

Source: `02_category_llm_youtube_databricks.py`

Validation-first LLM bakeoff for assigning one topic/category to each channel.
The machinery ports well; the taxonomy does not.

- `[YT-ONLY]` YouTube 15-class taxonomy: Film & Animation, Autos & Vehicles,
  Music, Pets & Animals, Sports, Travel & Events, Gaming, People & Blogs,
  Comedy, Entertainment, News & Politics, Howto & Style, Education, Science &
  Technology, Nonprofits & Activism.
- `[ADD]` Telegram needs a new topic taxonomy. Candidate axes may include news,
  politics, military/conflict, conspiracy, health, finance/crypto, religion,
  entertainment, sports, lifestyle, education, tech, commerce, scams/spam,
  official institutions, activism, and local/community channels. Final classes
  should be piloted before full bakeoff.
- `[REMAP]` Label normalization and alias map. Generic mechanism; category IDs,
  names, and aliases are Telegram-specific.
- `[REMAP]` Reference-label source selection. YouTube defaults to video
  `ai_label` or channel/expert labels. Telegram needs message-level labels,
  channel-level labels, external lists, or expert-coded labels.
- `[PORT]` Message/video-to-channel reference aggregation. Majority vote with
  minimum evidence count and agreement fraction.
- `[PORT]` Reference-label coverage summary.
- `[REMAP]` Prompt assembly. YouTube uses channel name, description, detected
  language, and recent video titles/descriptions. Telegram should use channel
  title, handle, bio/about, representative recent posts, pinned messages, media
  captions, and maybe forwarded-origin context.
- `[PORT]` Language-stratified deterministic sampling. Supports labeled
  validation, unlabeled pilot, full unlabeled, and all-channel modes.
- `[PORT]` Provider/model bakeoff across frontier and smaller models.
- `[PORT]` Provider-specific JSONL request formatting, optional batch submission,
  and batch-file registry.
- `[PORT]` Result parsing and prediction normalization, including strict enum
  validation, confidence clamping, ambiguous flag, parse-error tracking, and
  token counts where available.
- `[PORT]` Overall evaluation: valid prediction rate, parse-error rate,
  accuracy against reference, mean confidence, ambiguous count.
- `[PORT]` Macro-F1, macro-precision, and macro-recall on a full model-by-class
  grid so missed classes count as zero.
- `[PORT]` Language-stratified accuracy.
- `[PORT]` Pairwise inter-model agreement, especially small-vs-frontier
  agreement.
- `[PORT]` Consensus preview by model vote count and mean confidence.
- `[PORT]` Decision gate before full-corpus classification: high reference
  agreement, strong macro-F1, stable cross-language performance, low parse
  errors, strong small-model/frontier agreement, and category-specific error
  analysis. If no small model is close, use teacher-student distillation.

## 5. Core Attention / Audience Analysis - Notebook 10

Source: `10_attention_manuscript_analysis_CLAUDE.py`

Central YouTube metric: weekly views, defined as elapsed-day-normalized change
in lifetime channel views between two snapshots:

`weekly_views = (views_t - views_t-k) / elapsed_days * 7`

Telegram should reproduce this if repeated message/channel view snapshots exist.
If only current cumulative views are available, this becomes a different
estimand and should be labelled accordingly.

### Corpus and Panel Engineering

- `[PORT]` Safe execution modes: manifest-only, smoke, core/full with explicit
  confirmation.
- `[PORT]` Anchor snapshot selection with completeness guard. Chooses latest
  sufficiently complete partition and prior partition nearest the target window.
- `[PORT]` Snapshot coverage export: row counts, completeness fractions, selected
  anchor/prior, elapsed days.
- `[PORT]` Weekly-view panel construction. Dedupes duplicate snapshot rows,
  computes raw deltas, floors/drops/keeps negatives by policy, and keeps
  missing-prior channels as unmeasured rather than zero.
- `[PORT]` Entry/exit/measurability status: new-to-panel, null weekly views,
  negative deltas.
- `[REMAP]` Core channel frame. Joins attention metrics, metadata, language,
  category, and optional diagnostics. Telegram needs analogous metadata and a
  Telegram topic table.
- `[PORT]` Language coverage and category/topic coverage diagnostics.
- `[PORT]` Traffic blocks: approximate equal-view-mass blocks via value bins,
  scalable without a global sort.
- `[REMAP]` Observed/design/bounded tiers. YouTube uses subscriber thresholds
  such as 10k and 1k. Telegram needs member/view/activity thresholds and may
  need coverage caveats.
- `[REMAP]` Video/post-level frame for production analysis. The framework ports,
  but YouTube video fields and Shorts logic do not.

### Discovery and Collection Diagnostics

- `[REMAP]` Discovery saturation: new channels per crawl batch and
  high-subscriber head saturation. Ports if Telegram collection has comparable
  crawl batches and discovery logs.
- `[PORT]` Benchmark overlap checks where external benchmark lists exist.
- `[PORT]` Collection-log summaries and source-data exports.

### Platform Composition

- `[REMAP]` Language -> category -> channel treemap of weekly views. Language
  axis ports; category axis needs Telegram taxonomy.
- `[PORT]` Category/topic composition across traffic blocks once the topic axis
  exists.
- `[PORT]` Major-language composition and Jensen-Shannon divergence across
  language markets.
- `[PORT]` Other-language and other-category pooling to conserve total attention
  mass rather than dropping the tail.
- `[PORT]` Category/topic missingness diagnostics and bounded estimates.

### Subscriber/Member Proxy Failure

- `[REMAP]` Subscriber/member count as proxy for attention. YouTube uses
  subscribers; Telegram should use members/subscribers where available.
- `[PORT]` Weekly views by log-size bin: p10, median, p90.
- `[PORT]` Views-per-subscriber/member dispersion and central tendency.
- `[PORT]` Inactive or unmeasured share by size bin.
- `[PORT]` Log-size vs log-attention correlation.
- `[PORT]` Proxy heterogeneity by language and topic.

### Threshold Capture and Concentration

- `[REMAP]` Threshold capture table. YouTube thresholds are 1k/10k/100k/1M
  subscribers. Telegram thresholds should be based on member counts or a
  validated exposure proxy.
- `[PORT]` Cumulative view-capture curve.
- `[PORT]` Rank buckets: top 100, top 1k, top 10k, top 100k, below.
- `[PORT]` Lorenz curve, Gini, and top-k view shares.
- `[PORT]` Actual view share per approximate traffic block for auditability.
- `[PORT]` Design-based estimator hooks for lower-rank / residual-tail estimates
  when sample design metadata exists.

### Age, Incumbency, and Language-Population Analyses

- `[REMAP]` Channel age/start-date by traffic block. Telegram can port this if
  channel creation date, first observed post, or first collected date exists.
- `[PORT]` Language rank by weekly views.
- `[PORT]` Weekly views, channel counts, speaker-population lookup, and
  views-per-speaker / engagement-vs-population diagnostics.

### Production, Posting, and Format

- `[YT-ONLY]` Shorts vs long-form classification using duration/post type.
- `[REMAP]` Production intensity vs attention rank. Telegram should replace
  upload counts by posting counts, media counts, or message counts over a fixed
  window.
- `[REMAP]` Supply-demand analysis: median attention vs upload/post volume by
  content type.
- `[REMAP]` Format/content-type view share. Telegram needs a native axis such as
  text-only, image, video, document, link post, forwarded post, poll, or reply
  thread.
- `[REMAP]` Upload/post-age view distribution. Ports if post timestamps and
  cumulative views are available over time.

### Robustness and Reviewer Checks

- `[PORT]` Negative-delta policy sensitivity.
- `[PORT]` Suspicion/quality-flag exclusion sensitivity if a Telegram suspicion
  flag table exists.
- `[PORT]` Language-gate sensitivity.
- `[PORT]` Weekly-vs-lifetime attention comparison if both measures exist.
- `[PORT]` Cross-checks against diagnostics/rank summaries where available.
- `[PORT]` Topic-missingness bounds: lower, missing-at-random, and adversarial
  upper bounds.
- `[PORT]` Run manifest, checksums, source-data manifests, small-cell
  suppression, row-count export caps, and Delta-plus-CSV aggregate exports.

## 6. Parallel Codex Attention Notebook Additions

Source: `notebooks/codex_youtube_attention_manuscript_analysis.ipynb`

This notebook overlaps with Notebook 10 but includes useful additional
diagnostics that should be retained as planning patterns.

- `[PORT]` Metadata inventory / table-existence check using schema-only or
  bounded reads before expensive scans.
- `[PORT]` Channel analysis frame quality summary.
- `[PORT]` Attention observation scope summary by size band and measurement
  status.
- `[PORT]` Snapshot date summary and panel-depth summary: number of capture
  dates, span, depth bins, and subscriber/member strata.
- `[PORT]` Anchor-date candidate table from collection logs and snapshot panel.
- `[PORT]` Category/topic coverage probe by source status.
- `[PORT]` Exact rank and traffic-block status table when global sorting is used.
  Useful as a warning if the method will not scale to the full Telegram corpus.
- `[PORT]` Comparison of silver-derived attention to diagnostics layer:
  correlations with past-year views/ranks and validation/public-release cuts.
- `[PORT]` Benchmark overlap with external top-list resources.
- `[PORT]` Source-data manifest listing aggregate outputs.
- `[PORT]` Interpretation checklist and open-items section for manuscript
  number insertion.

## 7. Data Resource and Existing Aggregate Surfaces

Source: `README_data_resources.md`, `AGENT_DATA_CONTEXT.md`,
`README_telegram_data_resources.md`, `AGENT_TELEGRAM_DATA_CONTEXT.md`

These are not all generated by the five core notebooks, but they document
analyses/resources already present in the YouTube environment. Telegram should
get an equivalent map before analysis work begins. A first Telegram map now
exists for `prod_tads.telegram`, `prod_tads.telegram_random_walk`, and
`prod_tads.telegram_too`.

- `[PORT]` Data resource map by schema/layer: raw ingest, shaped entity tables,
  metrics tables, gold aggregates, diagnostics, validation, threshold
  collections, and model-output tables.
- `[PORT]` Canonical entity surfaces: channel metadata, video/message metadata,
  channel metrics, video/message metrics. In Telegram, the observed source
  tables are `tg_sl_channels`, `tg_sl_channels_metrics`, `tg_sl_posts`,
  `tg_sl_posts_metrics`, `tg_sl_comments`, and `tg_sl_comments_metrics`.
- `[ADD]` Metric snapshot surfaces. Telegram channel/post metrics are time
  series. Build explicit latest/max/windowed snapshots before constructing
  gold channel/message frames.
- `[ADD]` Join-type QA. `tg_sl_posts.channel_id` appears as `bigint` while
  channel and metric tables use string channel IDs; cast explicitly and test
  join loss.
- `[PORT]` Collection and ingest QA: collection summary, ingestion-by-minute,
  freshness distribution, publication timeline, videos/posts per channel
  histogram.
- `[PORT]` Language distribution aggregate. For Telegram, distinguish source
  metadata language, LID output, and panel-adjudicated language.
- `[YT-ONLY]` Video length distribution. Telegram equivalent would be media
  duration or message/media type distribution.
- `[REMAP]` Channel leaderboard. Telegram should define leaderboard by members,
  weekly views, forwards, reactions, or composite attention.
- `[REMAP]` Ad-vs-organic by channel. Telegram likely needs a different
  promotional/commercial-content or paid-forwarding/spam signal.
- `[PORT]` Diagnostics and validation/public-release cuts.
- `[REMAP]` Threshold collection tables. YouTube has 1k/5k subscriber threshold
  collection support; Telegram needs threshold strata based on actual available
  member/attention measures. The available candidate metric is
  `follower_count`; confirm whether it means channel subscribers, group
  members, or a cross-platform follower abstraction.
- `[PORT]` Model artifact and output table registry.
- `[ADD]` Random-walk source gap. The visible random-walk schema has
  `telegram_random_walk.tg_bz_ingest` with `depth`, `id`, `parentId`, `status`,
  `messages`, `timestamp`, and `error`, but no clean walk-event, validation,
  exposure, chain, or edge-list tables were visible. These must be derived or
  supplied from crawler logs before population-estimation claims.
- `[ADD]` Telegram scale-specific descriptive safeguards. The current
  `telegram_too` gold summary reports 29,099,371 posts across 1,662 channels,
  zero comments in the collection summary, 177 provisional language values,
  about 23.9% `NO TEXT` posts, and about 98.8% of posts in channels with more
  than 2,000 collected posts. Telegram descriptive notebooks must separate
  channel-weighted and post-weighted summaries, audit comment coverage, and add
  no-text/media-heavy language handling.

## 8. Telegram TOO Crawl and Sample-Construction Methods

Source: `/Users/hindman/Downloads/Hindman-telegram-read ahead revised (2).pdf`

The PDF adds a separate family of methods that precedes language/topic/attention
analysis: the Telegram top-of-the-ocean sample is built from a random-walk-style
link-tracing crawl. These analyses are needed to support the sample-frame,
population-estimation, denominator, and coverage claims in the methods section.

### Crawl Artifacts and Data Contracts

- `[ADD]` Source-to-artifact derivation audit. Before implementing estimator
  logic, determine whether `prod_tads.telegram_random_walk.tg_bz_ingest`
  fields such as `depth`, `id`, `parentId`, `status`, `messages`, `timestamp`,
  and `error` can reconstruct crawl steps and parentage. If not, require
  external crawler logs for walk events, validation outcomes, exposures, and
  random seeds.
- `[ADD]` Walk-record table. One row per walk step with chain ID, session ID,
  step index, layer/buffer state, source channel, selected target channel,
  transition type, timestamp, exposure index, and terminal status. Transition
  types should distinguish forward edge, probabilistic walkback/restart, and
  forced walkback/dead-end restart.
- `[ADD]` Edge-list table. One row per directed Telegram-channel link discovered
  while scanning a source channel, including source channel, target username or
  channel ID, validation status, timestamp, followed/skipped flag, reason
  skipped, source message/post identifier if retained, and duplicate-collapsed
  link key.
- `[ADD]` Channel metadata table from mapping crawl. For every visited or
  successfully validated target: channel ID, username/handle, title,
  subscriber/member count, total message count, total view count if available,
  most recent post timestamp, public/private status, chat type, validation
  status, and first/last seen timestamps.
- `[ADD]` Inclusion/exclusion audit. Counts and rates for channels excluded
  because they are dead ends, have no messages, fall below `cfg.MinUsers`, fail
  the recency threshold, are not public broadcast/supergroup targets, are
  private/deleted/inaccessible, or fail API validation.
- `[ADD]` Link-extraction and validation QA. For each scanned source: raw
  Telegram URLs found, distinct eligible target usernames after within-source
  duplicate collapse, validation attempts, validation successes, failures,
  SearchPublicChat/API errors, and rate-limit delays.
- `[ADD]` Crawler/validator throughput QA. Separate account-level and IP-level
  rate-limit exposure, per-client validation load, 2-second validation-delay
  compliance, failed/retried validations, and crawl throughput by hour/day.
- `[ADD]` Parallel-chain execution QA. The PDF treats walk chains as sampling
  units and pods/connections as workers. Track which worker processed each
  queued channel, but keep chain ID and random seed as the inferential unit.

### Walk Process Diagnostics

- `[ADD]` Seed-set construction audit. Document seed sources, deduped valid seed
  count, seed metadata coverage, seed subscriber/member distribution, seed
  language/topic if available, and overlap with previously discovered channels.
- `[ADD]` Random starting-point audit. At each session, verify that starting
  channels are sampled from the seed frame according to the intended design
  and record the exact seed draw probabilities if nonuniform.
- `[ADD]` Walk-decision audit. For every processed channel, record the number of
  new validated targets, whether a forward step was available, whether the step
  followed a uniformly random new target, whether the 15% restart rule fired,
  and whether a forced walkback occurred.
- `[ADD]` Step-type mix over time. Monitor forward edges, probabilistic
  walkbacks, and forced walkbacks by chain and exposure bin; this is one of the
  burn-in diagnostics.
- `[ADD]` Dead-end and failure-rate diagnostics. Report dead ends, stale
  channels, failed validations, no-new-target channels, and terminal-state
  rates by chain, time, subscriber tier, and source list.
- `[ADD]` Layer/buffer balance diagnostics. Because the crawler processes layers
  in parallel to avoid one chain racing ahead into a corner of the graph, report
  layer sizes, unfinished-channel backlog, terminal-state waits, and
  chain/worker imbalance.

### Exposure Accounting

- `[ADD]` Validated-link exposure axis. Construct cumulative exposure `E` as
  the number of distinct eligible public-channel targets extracted from each
  processed source and submitted for validation, with within-source duplicates
  collapsed. This is the x-axis for population estimation, not raw steps or raw
  URL tokens.
- `[ADD]` Exposure-bin table. Bin post-burn-in exposure into equal-exposure
  intervals; for each bin and threshold, store newly discovered channels,
  eligible exposure, discovery rate, and chain contributions.
- `[ADD]` Discovery event table. A channel enters the discovered set when
  validation succeeds, whether or not the walker follows it. Store first
  validation time, first exposure index, first-discovery source, first-discovery
  chain, and whether it was followed or skipped at discovery.
- `[ADD]` Threshold grid. Define subscriber/member thresholds `K` and a floor
  `M = cfg.MinUsers`; all population estimates refer to reachable public
  channels satisfying the inclusion rules, not all Telegram channels.

### Burn-In and Convergence Diagnostics

- `[ADD]` Burn-in selection. Estimate and record the post-seed burn-in boundary
  at the chain level. Only post-burn-in data enter estimation, while
  pre-burn-in discoveries remain as the offset already discovered at burn-in.
- `[ADD]` Burn-in observables. Monitor log subscriber count of newly discovered
  channels, discovery rate per exposure bin at operative thresholds, and
  forward/walkback/forced-walkback mix.
- `[ADD]` Rank-normalized split-Rhat diagnostics. Compute Rhat across chains
  for burn-in/convergence observables and require sustained values below the
  operational threshold, with the caveat that this is a heuristic rather than a
  proof of mixing.
- `[ADD]` Cross-chain threshold consistency. At checkpoints, truncate all chains
  to common post-burn-in exposure, recompute threshold estimates by chain, and
  report interval overlap, Rhat, and separation between parametric asymptotes
  and Chao2 lower bounds.
- `[ADD]` Rolling-window stability. Track stability of threshold counts,
  subscriber/view denominator estimates, and coverage estimates over the last
  rolling exposure window.

### Threshold Count and Population Estimation

- `[ADD]` Post-burn-in accumulation curves. For each threshold `K`, compute
  discovered-at-burn-in count, cumulative post-burn-in discoveries as a
  function of exposure, and estimated unseen remainder.
- `[ADD]` Random-walk saturation curves for channel counts. Fit simple
  exponential and stretched-exponential accumulation models to binned discovery
  increments, not raw cumulative counts. These estimate discovered-channel
  count saturation under the crawl design; they are distinct from the
  rank-size tail-mass estimator below.
- `[ADD]` Held-out predictive model selection for count saturation. Choose
  between random-walk saturation forms using held-out later exposure windows
  rather than AIC on cumulative curves.
- `[ADD]` Chao2 lower-bound estimates. Treat independent walk chains as
  replicated samples; truncate chains to common post-burn-in exposure; compute
  distinct discoveries, singleton-across-chain counts, doubleton-across-chain
  counts, and the bias-corrected Chao2 lower bound for each threshold.
- `[ADD]` Rarity / unseen-fraction lower-bound indicator. Report the gap between
  observed discoveries and Chao2 lower bound, clearly labelled as a lower-bound
  diagnostic rather than a true unseen-fraction estimate.
- `[ADD]` Monotonized subscriber/member survival curve. Enforce that estimated
  `N>=K` is nonincreasing in `K`, with Chao2 floors, using isotonic regression
  or an equivalent monotone adjustment.
- `[ADD]` Threshold-estimate comparison table. For every `K`, report observed
  count, curve estimate, Chao2 lower bound, monotonized estimate, bootstrap
  interval, and convergence/stability status.

### Rank-Size Tail Estimator for Missing Audience Mass

The newer tail-estimator materials describe a separate analysis for estimating
unobserved mass below a reliable observed head. This should be used for
subscriber/member mass and, if selected, view mass. It is not a random-walk
species estimator, and the nested degree estimates are sensitivity estimates,
not a confidence interval.

- `[ADD]` Ranked metric table. Build one deduplicated ranked table per audience
  metric: `rank`, `canonical_channel_id`, `metric_value`, source provenance,
  last-observed timestamp, and eligibility flags. For YouTube this was
  `view_count`; for Telegram the likely v1 metrics are member/subscriber count
  and a carefully defined view measure.
- `[ADD]` Trusted-head / censoring-boundary selection. Choose candidate
  boundaries `r_c` where the observed head is believed complete enough to
  anchor extrapolation. Diagnostics should include head-closure evidence from
  crawl saturation/Chao2, source-list overlap, recent-discovery rates above the
  boundary, and operational confidence that high-rank channels are not missing.
- `[ADD]` Boundary suitability checks. For each candidate `r_c`, require enough
  observed ranks in the fitting window, usually at least about 1,000; positive
  nonzero metric values; a concave log-log rank-size curve near the boundary;
  local Pareto exponent `alpha0 > 1` if the degree-0 power-law tail is to be
  finite; and a reasonably stable curvature parameter `eta0`.
- `[ADD]` Log-log derivative diagnostics. Plot `log(metric_value)` against
  `log(rank)`, then estimate and plot local slope, local Pareto exponent
  `alpha(x) = -z'(x)`, and curvature/steepening `eta(x)`. The key empirical
  check is whether the slope steepens into the tail rather than remaining
  constant.
- `[ADD]` Boundary anchor `y0`. Estimate the metric value at `r_c` using a
  narrow local-linear smoother around the boundary, not the intercept from a
  wide quadratic fit. This prevents a concave curve from starting the
  extrapolated tail below the observed boundary value.
- `[ADD]` Local quadratic fit for `alpha0` and `eta0`. Fit a tricube-weighted
  local quadratic to `log(metric)` on `log(rank)` in the window immediately
  below `r_c`. Use this to estimate `alpha0` and `eta0`, with `eta0` clipped to
  nonnegative when the intended model assumes monotone steepening.
- `[ADD]` Staggered local quadratics for higher curvature. Repeat the local
  quadratic fit at shifted boundaries such as `r_c`, `r_c / exp(delta)`, and
  `r_c / exp(2 * delta)` to estimate `eta1` and `eta2` from finite differences.
  Clip higher curvature terms to nonnegative for the nested sensitivity ladder,
  while documenting that this is a modeling assumption rather than a theorem.
- `[ADD]` Implementation audit for derivative formulas. Reconcile the notes and
  code before porting: the explainer describes a second-order backward
  difference for `eta1`, while the attached Databricks script uses a simpler
  one-step difference. Pick one formula, document it, and keep the notebook,
  methods text, and code aligned.
- `[ADD]` Nested degree-0 through degree-3 tail estimates. Fit and report four
  models: degree 0 constant `alpha` power law; degree 1 constant `eta`; degree
  2 accelerating steepening; degree 3 one additional curvature derivative.
  Under the nonnegative shape restrictions, the missing-mass estimates should
  be weakly ordered `D0 >= D1 >= D2 >= D3`.
- `[ADD]` Continuous tail integration. Compute tail mass as the observed
  boundary value times `r_c` times the integral over log-rank distance beyond
  `r_c`. Use the closed-form power-law tail for degree 0 when `alpha0 > 1`,
  and adaptive numerical quadrature for higher degrees.
- `[ADD]` Finite-support and discrete variants. If Telegram analysis has a
  credible maximum reachable rank or a moderate discovered denominator, run a
  finite-support version with upper limit `log(R_max / r_c)` and, where
  practical, a discrete predicted-rank sum rather than only the infinite
  continuous-tail approximation.
- `[ADD]` Boundary sensitivity grid. Run the estimator at several plausible
  `r_c` values and report how `alpha0`, `eta0`, `eta1`, `eta2`, unobserved
  tail percentage, and implied coverage change. Divergence across boundaries
  should be treated as substantive uncertainty, not smoothed away.
- `[ADD]` Model-family sensitivity interpretation. Treat degree 0 as the
  familiar constant-Pareto upper-tail extrapolation, degree 1 to 3 as
  progressively stronger curvature assumptions, and the spread as a sensitivity
  ladder. Do not label `D3` as truth or the degree spread as a statistical
  confidence interval.
- `[ADD]` Applicability failures. Flag cases where the rank-tail estimator
  should not be used or should be secondary: fewer than roughly 1,000 fitting
  ranks, convex/heavier-than-Pareto behavior near the boundary, unstable
  derivative estimates, no trusted observed head, strong metric censoring, or
  inconsistent source coverage.
- `[ADD]` Distributed implementation plan. For large ranked tables, implement
  ranking with a full distributed sort, cache the ranked view, compute local
  weighted least-squares sufficient statistics in Spark, solve only the small
  normal equations on the driver, and collect only a log-spaced plotting sample.
- `[ADD]` Tail-estimator output table. For each metric and boundary, report
  `r_c`, `y0`, `alpha0`, `eta0`, `eta1`, `eta2`, observed mass through `r_c`,
  tail mass and total mass under D0-D3, tail percentage, observed coverage,
  fitting-window size, and boundary diagnostics.
- `[ADD]` Methods-positioning comparison. In the writeup, distinguish this
  estimator from pure Pareto/Zipf extrapolation, rank-size OLS corrections,
  Clauset-Shalizi-Newman power-law testing, Hill/EVT/GPD tail-index methods,
  Good-Turing/unseen-species estimators, and global parametric families. The
  defensible claim is narrower: a boundary-local, shape-constrained estimator
  for finite missing rank mass.
- `[ADD]` Literature-neighbor framing. Describe second-order EVT and
  reduced-bias Hill methods as the closest methodological neighbors,
  generalized Pareto curves as the closest conceptual neighbor, missing-rich
  wealth estimation as the closest applied analogue, and local-polynomial
  smoothing as the estimation machinery. This prevents the Telegram methods
  section from overstating novelty while still explaining the estimator's
  platform-data contribution.

### Subscriber and View-Mass Denominators

- `[ADD]` Head-closure threshold selection. Choose a high threshold `H` where
  the observed head is effectively enumerated: observed count agrees with the
  Chao2 lower bound, chain-bootstrap discoveries above `H` are stable, and the
  observed head mass can be treated as exact.
- `[ADD]` Observed head mass. Compute exact observed subscriber/member mass and
  view mass above `H`.
- `[ADD]` Subscriber/member denominator via rank-tail estimator. Use the
  rank-size tail estimator to estimate mass below the trusted head boundary:
  observed head mass plus D0-D3 missing-mass estimates. Report a preferred
  estimate only after boundary and model sensitivity are reviewed; otherwise
  present the nested ladder as the primary result.
- `[ADD]` Cross-check against threshold survival reconstruction. Keep the
  monotonized threshold survival curve and Riemann-sum bounds as an independent
  denominator cross-check, especially when random-walk discovery is still
  incomplete. The rank-tail estimator estimates mass by rank geometry; the
  Chao/saturation machinery estimates discovery/count completeness.
- `[ADD]` Conservative coverage denominator choice. For headline lower-bound
  coverage, use a conservative high-denominator scenario such as degree 0 or
  the upper bootstrap/boundary-sensitivity denominator, unless the team
  explicitly justifies a curvature-corrected denominator as the headline.
- `[ADD]` View denominator reconstruction. Repeat the rank-tail workflow for
  views if the committee elects to use views or both views and subscribers.
  Document the exact view measure: channel total views, sum of retained-message
  views, recent-post views, or another consistently collected metric.
- `[ADD]` View-deletion / retention sensitivity. Because Telegram channels can
  auto-delete messages, evaluate how recorded total views may undercount actual
  lifetime views; report missing/deleted-message indicators, retention-window
  metadata where available, and sensitivity of view coverage to the chosen view
  measure.

### Coverage Claims and Candidate TOO Cuts

- `[ADD]` Candidate sample construction. Rank discovered channels by subscriber
  count, view count, or both; select top `N` or threshold-defined sets; compute
  exact numerator mass for each candidate sample.
- `[ADD]` Subscriber/member coverage estimates. For any proposed sample `T`,
  compute point coverage, lower confidence limit, and upper confidence limit
  using denominator uncertainty. The headline claim should use the conservative
  lower confidence limit.
- `[ADD]` View coverage estimates. Same as above for views if views are a v1
  criterion or a parallel committee option.
- `[ADD]` Coverage-vs-threshold curve. For candidate thresholds and `N` values,
  report sample size, subscriber/member mass, view mass, coverage point
  estimates under D0-D3 denominators, bootstrap/boundary-sensitivity intervals,
  and lower confidence limits.
- `[ADD]` Stopping-rule dashboard. The crawl is ready when the lower confidence
  limit meets the target coverage, interval half-width is below tolerance,
  denominator estimates are stable over a rolling exposure window, and
  operative threshold and rank-tail estimates are stable.
- `[ADD]` Views-vs-subscribers decision analysis. Compare rank correlation,
  concentration, coverage curves, and sample membership churn between
  subscriber-based, view-based, and combined cuts.
- `[ADD]` Superlinearity analysis. Test whether views are more concentrated
  than subscribers by comparing Lorenz/Gini/top-k shares and log-log slopes of
  views on subscribers.
- `[ADD]` Committee options table. Present subscribers-only, views-only, and
  combined candidate samples with thresholds, sample sizes, coverage LCLs, and
  methodological caveats.

### Chain-Level Bootstrap and Uncertainty

- `[ADD]` Chain-level bootstrap. Resample whole post-burn-in chains with
  replacement, preserving within-chain ordering and exposures. Do not resample
  individual steps as independent.
- `[ADD]` Equal-exposure truncation per bootstrap replicate. Ensure all
  resampled chains are compared at common post-burn-in exposure.
- `[ADD]` Bootstrap recomputation pipeline. For each replicate, recompute Chao2
  incidence counts, refit random-walk saturation curves, monotonize threshold
  estimates, rebuild the ranked audience-metric table, rerun the rank-tail
  estimator at the chosen boundaries, reconstruct denominators, and recompute
  sample coverage.
- `[ADD]` Boundary bootstrap and sensitivity. In addition to chain resampling,
  rerun the rank-tail estimator across the predeclared boundary grid. Coverage
  uncertainty should include both stochastic crawl uncertainty and sensitivity
  to the trusted-head boundary.
- `[ADD]` Model-ladder coverage range. For each candidate sample, compute
  coverage under D0-D3 denominators. Use the D0 denominator as a conservative
  constant-Pareto lower-coverage scenario when the log-log curve is concave;
  report D1-D3 as curvature-corrected sensitivity estimates.
- `[ADD]` BCa or percentile intervals. Prefer BCa bootstrap intervals when
  numerically stable; otherwise use percentile intervals. Clamp denominator
  draws upward to Chao2 floors and to the observed head mass.
- `[ADD]` No synthetic chain concatenation. If pooled curves are fit, use
  original timestamp interleaving or chain-level summaries, not arbitrary serial
  concatenation of chains.
- `[ADD]` Moving-block bootstrap sensitivity. Report exposure-binned
  moving-block bootstrap as a secondary sensitivity check.

### In-Degree and Discoverability Sensitivities

- `[ADD]` Observed in-degree table. From the edge list, compute observed inbound
  links for discovered channels, clearly marking that this is observed in a
  partially observed graph.
- `[ADD]` Inverse-observed-degree sensitivity summaries. Report
  discoverability-weighted summaries such as weighted subscriber/view
  distributions or topic/language composition. Do not present these as the
  basis of the v1 coverage claim unless a design-based inclusion-probability
  argument is established.
- `[ADD]` Followed-vs-skipped edge comparison. Compare properties of targets
  selected as next hops against skipped validated targets to audit the random
  next-step rule and discoverability bias.

### Missed-Audience Sensitivity

- `[ADD]` Audience-risk framing. Define missed-audience risk in subscriber and
  view mass, not only in channel count. Large numbers of small missed channels
  may matter less than a small missed high-audience basin.
- `[ADD]` Clustering graph. Build a graph of validated channels using organic
  Telegram links discovered in scanned messages; include followed and skipped
  edges; exclude artificial walkbacks, forced walkbacks, and restarts.
- `[ADD]` Hub-deweighted, symmetrized community detection. Use multi-resolution
  clustering on the giant weak component and retain isolated components where
  appropriate. Treat results as crawl-discovery clusters, not definitive social
  communities.
- `[ADD]` Inference graph. Preserve the full directed, time-stamped crawl
  record: chain ID, exposure index, source, validated targets, followed target,
  and skipped targets.
- `[ADD]` Consensus clustering and hierarchy. Run stochastic community
  detection repeatedly, aggregate by consensus clustering, and collapse
  unstable fine clusters to the smallest stable parent.
- `[ADD]` Chain-bootstrap cluster stability. Resample whole chains, rebuild the
  clustering graph, rerun community detection, match reference clusters to
  bootstrap analogues, and report stability.
- `[ADD]` Audience presence statistic. For each cluster and audience measure,
  estimate the probability that a bootstrap replicate recovers at least 80% of
  the original cluster audience.
- `[ADD]` Audience-weighted Jaccard recovery. Report mean, lower percentile,
  and dissolution rate; keep unweighted Jaccard as secondary.
- `[ADD]` Pairwise consensus / PAC. Compute pairwise co-clustering
  probabilities and weighted proportion of ambiguous clustering to assess
  reproducibility.
- `[ADD]` Leakage and merge/split diagnostics. Identify clusters whose audience
  repeatedly leaks to or merges with other bootstrap clusters.
- `[ADD]` Cluster stability status table. Classify high-confidence
  audience-stable clusters, usable stable clusters, boundary-unstable but
  audience-stable basins, single-chain/weakly supported clusters, and unstable
  clusters.
- `[ADD]` First-discovery parentage. For every discovered channel, record the
  seed or source channel that first exposed it.
- `[ADD]` Dependency-adjusted discovery basins. For each stable cluster, compute
  channels whose first-discovery path depends on that cluster, and a
  conservative version excluding independently rediscovered downstream
  channels.
- `[ADD]` Basin audience. Compute subscriber and view mass for each dependency
  basin.
- `[ADD]` Seed-entry intensity. Estimate each cluster's chance of entry via
  random seed starts, using exact seed draw probabilities when nonuniform.
- `[ADD]` Independent outside-link entry intensity. Count independent scanned
  source channels outside the cluster and its dependency closure that exposed at
  least one target inside the cluster.
- `[ADD]` Audience-normalized entry visibility. Estimate independent entry
  opportunities per unit of subscriber or view share for each basin.
- `[ADD]` Dark-audience omission bounds. Compare hypothetical unseen basins
  against the lower tail of observed stable basins and report omission
  probabilities under `kappa = 1, 10, 30, 100, infinity`.
- `[ADD]` Partial-discovery diagnostics. For observed stable clusters, reconstruct
  within-cluster audience discovered after first entry as a function of internal
  exposure; censor after the first 5%, 10%, and 20% of cluster-channel
  discoveries and measure subscriber/view mass recovered.
- `[ADD]` Within-cluster saturation. Apply saturation, Chao2, and bootstrap
  diagnostics within clusters where exposure is sufficient.
- `[ADD]` Missed-audience reporting package. Include high-audience cluster
  table, stability table, dark-audience sensitivity table, and partial-discovery
  diagnostic. Keep the headline claim as a reachable-population coverage claim,
  not a representativeness guarantee.

### Researcher-Facing Outputs and Denominator Tools

- `[ADD]` Final TOO sample frame. Selected channels above the subscriber/view
  cut, with coverage estimates, inclusion threshold, provenance, and downstream
  post-ingestion status.
- `[ADD]` Post-ingestion audit for selected channels. The mapping crawl only
  collects metadata; the TOO ingestion crawl must report post collection
  coverage, date ranges, message counts, views/reactions/forwards where
  available, failures, and inaccessible channels.
- `[ADD]` Discovered-channel list with population estimates. Release or
  internally maintain all discovered channels with estimated denominator
  context, so researchers can compare external Telegram datasets to the
  subscriber/view distribution.
- `[ADD]` Arbitrary-subset coverage calculator. Given a user-defined subset of
  discovered or TOO channels, compute observed numerator mass and coverage
  against the estimated denominators, with caveats for undiscovered channels.
- `[ADD]` Sample provenance labels. For every channel/post in the TOO, include
  mapping-crawl provenance, ingestion-crawl provenance, threshold status, and
  whether coverage claims are inherited or recomputed.
- `[ADD]` Non-representativeness warnings. Explicitly label the TOO as a
  high-reach curated sample with quantified coverage, not a representative
  probability sample and not a complete channel frame.
- `[ADD]` Public denominator release package. If population estimates will be a
  public resource, define versioned tables, confidence intervals, threshold
  grids, methods notes, and update cadence.

### V2 Coverage Extensions

- `[ADD]` Language-specific coverage estimates after LID validation. Once
  Telegram LID is validated, compute subscriber/view coverage by language and
  uncertainty where feasible.
- `[ADD]` Topic-specific coverage estimates after topic validation. Once the
  Telegram taxonomy is validated, compute coverage by topic/category.
- `[ADD]` Activity-level coverage. Add posting frequency, recent activity,
  active-channel status, and engagement coverage as v2 criteria if needed.
- `[ADD]` View/subscriber mapping validation. Estimate how subscriber mass maps
  to view mass, including superlinearity and deletion/retention biases.

## 9. Telegram-Specific Downstream Analyses to Add

These are not in the YouTube code but are likely first-class Telegram needs.

- `[ADD]` Forwarding / cross-posting network: edges from forwarded-from,
  mentioned, linked, or reposted channels; centrality and community detection.
- `[ADD]` Message-level diffusion: forwards, reshares, views over time, and
  cascade-like behavior if timestamped snapshots exist.
- `[ADD]` Reaction/reply engagement: reaction counts, reply counts, comment
  thread availability, and engagement-per-view.
- `[ADD]` Channel type and access status: public channel vs group, private,
  inaccessible, deleted, invite-only, mirrored, bot/admin-operated.
- `[ADD]` Content-type axis replacing Shorts/long-form: text, image, video,
  document, link, poll, voice/audio, sticker, forwarded post, mixed media.
- `[ADD]` URL/domain/link analysis: outbound domains, platform links, repeated
  link farms, and news-source categories.
- `[ADD]` Hashtag/mention analysis: topical tags, coordinated mentions, and
  entity handles.
- `[ADD]` Source-list provenance and collection bias: how channels entered the
  corpus, by list/source/crawl method, with overlap and saturation diagnostics.
- `[ADD]` Multilingual and translation behavior: channels that switch language
  over time, post bilingual text, or cross-post translations.
- `[ADD]` Spam/scam/commerce diagnostics if the Telegram corpus includes
  crypto, investment, counterfeit, gambling, or other high-risk categories.
- `[ADD]` Temporal event responsiveness: burst analysis around geopolitical,
  election, crisis, or news events if dates are central to the Telegram study.

## Porting Priority

1. Use the Telegram data-resource map to build entity/metric canonical
   surfaces from `prod_tads.telegram_too.tg_sl_*` and source-gap reports for
   random-walk artifacts.
2. Build metric snapshot tables for `follower_count`, `views_count`,
   `post_view_count`, post shares/comments/likes, and reaction aggregates.
3. Audit and build the random-walk crawl analysis tables: walk records, edge
   list, channel metadata, exposure accounting, validation QA, and chain
   metadata. Do not assume these already exist in `prod_tads`.
4. Implement the TOO population-estimation stack: burn-in diagnostics,
   random-walk saturation curves, Chao2 lower bounds, monotone survival curves,
   rank-size tail-mass estimation, denominator reconstruction, chain/bootstrap
   and boundary-sensitivity intervals, coverage dashboards, and missed-audience
   sensitivity.
5. Finalize the v1 TOO sample cut by subscriber mass, view mass, or both; then
   run the second-stage post ingestion crawl for selected channels.
6. Port LID v3 on Telegram segments with remapped fields and recalibrated
   weights.
7. Run LID validation cohorts and LLM language panel on contested cases.
8. Design and validate Telegram-native topic taxonomy using the Notebook 02
   bakeoff machinery.
9. Rebuild the attention frame from repeated Telegram view/member snapshots.
10. Reproduce concentration, proxy-failure, composition, language-market, and
   robustness analyses.
11. Replace YouTube-only format analyses with Telegram content-type, forwarding,
   reaction, and link-network analyses.
