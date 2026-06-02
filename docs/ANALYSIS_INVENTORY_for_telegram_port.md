# YouTube Analysis Inventory — drafting document for the Telegram port

Purpose: a complete, itemized list of every analysis currently run on the YouTube
corpus, tagged for portability to Telegram. Built from the five core notebooks in
`src/`:

| # | File | Analysis family |
|---|------|-----------------|
| 01 | `01_language_openlid_v3_databricks.py` | Dual-model language detection (LID v3) |
| 01b | `01b_language_lid_v3_subscriber_cohort_analysis_databricks.py` | Subscriber-cohort LID driver |
| 02 | `02_category_llm_youtube_databricks.py` | LLM channel category/topic classification |
| 03 | `03_language_llm_panel_databricks.py` | LLM language-adjudication panel |
| 10 | `10_attention_manuscript_analysis_CLAUDE.py` | Core attention/audience manuscript analysis |

**Portability tags used throughout:**
- 🟢 **PORT** — corpus-agnostic; carries to Telegram with at most a field-name remap.
- 🟡 **REMAP** — method ports, but YouTube field set / weights / taxonomy must be re-mapped to Telegram fields.
- 🔴 **YT-ONLY** — depends on a YouTube-only signal (Shorts, video tags, `topic_categories`, declared `defaultLanguage`); needs a Telegram-native substitute or is dropped.

A YouTube "channel" → Telegram channel/group; a YouTube "video" → Telegram message/post.

---

## 1. Language detection — Notebook 01 (LID v3, dual-model)

Measures the **dominant written-metadata language** of each channel (not spoken/content
language). Two fastText models run independently and are reconciled into a consensus.

### Source prep & segmentation
- 🟢 **Deterministic dedup** of channels & videos (never `dropDuplicates`; timestamp → SHA-256 row-hash ordering). QA table `yt_lid_v3_dedupe_qa`.
- 🟢 **Deterministic smoke-test sampling** (`xxhash64(channel_id)` order) and **bucketed resumable runs** (`channel_hash_bucket = pmod(xxhash64(channel_id), 4096)`, Delta `replaceWhere`).
- 🟡 **Most-recent-N-videos-per-channel** cap (default 10) → maps to recent-N-messages-per-channel.
- 🟡 **Canonical segment table** `yt_lid_v3_segments_input`: one row per text field. YouTube segment types = `channel_name`, `channel_description`, `video_title`, `video_description`, `video_tags` (truncated 2000 chars). Telegram has no titles/tags → remap to channel name, bio/about, message text.
- 🟢 **Per-script letter metrics** (pandas UDF): Unicode letter counts per script (Latin, Devanagari, Arabic, Cyrillic, Han, Kana, Hangul, Thai…), dominant script + share, URL/hashtag/emoji flags.
- 🟢 **Text-validity rule** `is_valid_text_for_lid`: ≥40 clean letters (Latin/ambiguous) OR (non-Latin dominant AND ≥12 letters AND dominant-script-share ≥0.60).

### Model inference
- 🟢 **OpenLID-v3 fastText** primary inference, top-k=5 per valid segment → `yt_lid_v3_openlid_predictions_compact`.
- 🟢 **GlotLID fastText** second model, matched preprocessing → `yt_lid_v3_glotlid_predictions_compact`. Optional native-preprocessing audit pass; optional low-confidence-only "audit_segments" mode.
- 🟢 **Label normalization** of `__label__xxx_Yyyy` → iso639_3 + script.
- 🟢 **Cross-model segment-universe parity check** (both models ran identical segment set; checksum parity).

### Channel-level aggregation (per model)
- 🟡 **Weighted vote construction**: top-1 admitted if score ≥0.20; top-2 if score ≥0.35 and ratio ≥0.50. `weighted_score = score × segment_weight × rank_weight`. Segment weights (video_title 2.0, channel_description 1.0, video_description 1.0, video_tags 0.5, channel_name 0.25) are YouTube-shaped → remap.
- 🟢 **Per-(channel,language) vote table** and **per-channel per-model summary** (`yt_lid_v3_channel_model_aggregation`): primary/secondary label, vote-share "confidence" proxy, rank-2/3 margins, full ranked vote JSON.
- 🟢 (default-off) experimental aggregation fixes (suppress Latin channel-name vote on non-Latin channels; bilingual status; romanized-Indic preference).

### Model comparison & consensus
- 🟢 **Analysis-cluster lookup** collapsing near-languages (Serbo-Croatian, Malay/Indonesian, Chinese Hans/Hant, North-Indic Hindi family, Romance, Arabic family).
- 🟢 **Segment-level model comparison** (`segment_agree_exact`/`_iso`/`_cluster`).
- 🟢 **Channel-level consensus classifier** (deterministic tiered `consensus_status`: insufficient_text → exact agreement → high-risk-tail handling → confidence fallback → Arabic taxonomy normalization → iso/script variant → cluster agreement → disagreement-needs-review). Emits `consensus_language_label`, `consensus_source`, `requires_manual_adjudication`.
- 🟢 **Consensus QA / agreement-rate audit** (exact / iso / within-cluster agreement rates).

### Specialized diagnostics
- 🟢 **Mixed-language detection**: permissive "screen" vs strict "credible" flags, requiring cross-model secondary support; rejection-reason coding → `yt_lid_v3_mixed_language_candidates`.
- 🟡 **Hindi/Indic recall diagnostics**: per-channel text features (Devanagari counts, romanized-keyword hits), priority-coded audit-candidate table. Mechanism is generic (a recall-audit template for any under-detected family); keyword lists are YouTube-flavored.
- 🟢 **High-risk tail-label redirect diagnostic**: flags 19 Latin tail labels models hallucinate (srd/ast/vec/gug/…), aggregates contradicting evidence. Tail set is LID-general, not YouTube.

### Final tables, validation, ablation, acceptance
- 🟢 **Final channel table** `yt_lid_v3_channels` (one row/channel; per-model + consensus + mixed + status fields).
- 🔴 **Optional source write-back** (MERGE consensus into `yt_sl_channels.detected_language`) — YouTube table-specific.
- 🟢 **Summaries**: `language_summary_full`/`_rollup`, `model_agreement_summary`, `suspect_tail_audit_sample`, `unclassified_audit`.
- 🔴 **`source_language_confusion`**: declared `defaultLanguage`/`detected_language` vs model — Telegram has no declared-language field; likely drop.
- 🟢 **Stratified manual-validation sample** (seeded, ≤100/stratum, 11 strata covering high-confidence, low-confidence, mixed, high-risk-tail, Indic-audit, disagreements, insufficient-text, non-Latin control).
- 🟢 **Ablation analysis** (re-aggregate stored predictions under alt configs: legacy weights, no-top2, weight variants, top1-only; report label churn vs default). No re-inference.
- 🟢 **Acceptance checks** (config + output-table + row-count invariants; raises on failure).

---

## 2. Subscriber-cohort LID driver — Notebook 01b

Wraps Notebook 01; builds two cohorts, runs the full pipeline per cohort, unions/compares.
Links **language outcome ↔ subscriber rank**. Essentially all 🟢 (subscriber field auto-detect
already lists `follower_count` first → maps straight to Telegram member counts).

- 🟢 **Subscriber parsing + deterministic channel dedup** (handles "1.2M/3k" text).
- 🟢 **Top-subscriber cohort** (top 100k by subscriber count; records exact cutoff & at-cutoff ties).
- 🟢 **Random-band comparison cohort** (seeded 100k sample, 10k ≤ subs ≤ top-cutoff, excluding the top cohort).
- 🟢 **Cohort metadata & ID tables**; cohort source materialization.
- 🟢 **Twin child-notebook runs** (Notebook 01 per cohort, distinct `run_id`).
- 🟢 **Combined channel results** joining subscriber rank to LID outcome.
- 🟢 **Language-status summary by cohort**, **consensus-language summary by cohort**, **review queue**, **model-agreement-by-cohort** comparison (high-subscriber vs random band).

---

## 3. LLM language-adjudication panel — Notebook 03

A 3-LLM panel that adjudicates only **contested / audit** channels from Notebook 01 — a
validation layer, not a population classifier. Depends on Notebook 01's `yt_lid_v3_*` tables.

- 🟢 **Three-LLM frontier panel** (OpenAI gpt-5.5, Anthropic claude-opus-4-7, Gemini gemini-3.1-pro-preview), one independent vote each, blind to fastText guess and to each other.
- 🟡 **Classifier system prompt**: judges dominant written-metadata language from supplied metadata; label = `<ISO639-3>_<ISO15924>`; encodes guardrails (Latin-name trap, romanization, creole vs English, minority-tail over-prediction, Arabic/Mandarin/Indonesian taxonomy normalization, abstention). Field set/weights are YouTube-shaped → remap; guardrails port as-is.
- **Routing rules (which channels get adjudicated):**
  - 🟢 **Model-disagreement route** (consensus_status ∈ disagreement/fallback/missing), excluding within-Arabic-family.
  - 🟢 **Unresolved high-risk-tail route** (tail label with NULL consensus only).
  - 🟡 **Shared-bias English↔Indic route**: both models say English but Devanagari/romanized/source-Indic evidence contradicts. Concept (catch shared model bias vs a script/keyword signal) ports; the Indic feature tables must be rebuilt.
  - 🟢 **Blind agreement-bucket audit sample** (deterministic 0.5% of "settled" channels to measure panel-vs-pipeline disagreement).
- 🟡 **Per-channel metadata prompt builder**: includes even fastText-invalid short segments as weak evidence (flagged inline). Logic generic; segment schema YouTube-shaped.
- 🟢 **Provider batch request fan-out + JSONL formatting** (OpenAI Responses/Chat, Anthropic Messages, Gemini Batch); optional submission via secrets.
- 🟢 **Provider-agnostic result parsing** + per-vote validity flag → `yt_lid_v3_llm_panel_raw_results`.
- 🟢 **Majority-vote reconciliation**: majority on base ISO (≥2 of 3) → modal full label preserving script + side fields; status `panel_majority` / `needs_human_review` / `no_panel_result` → `yt_lid_v3_llm_panel_verdicts`.
- 🟢 **Per-provider label + reach breakout** (per-model agreement/coverage).
- 🟢 **Consensus-source / provenance tagging** (`llm_panel` / `human_review` / `audit_sample`; audit rows never overwrite pipeline label).
- 🟢 **Coverage assertion** (one verdict per routed channel).
- 🟢 **Blind-audit evaluation metric** — headline: how often the panel disagrees with the pipeline on "confident" labels (estimates pipeline error rate).

---

## 4. LLM channel category / topic classification — Notebook 02

A validation-first LLM "bake-off" assigning each channel one category, benchmarked against
reference labels, with inter-model agreement. **The taxonomy is the most YouTube-bound piece.**

- 🔴 **15-class category taxonomy** (`YT_CATEGORIES`: Film & Animation, Autos, Music, Pets, Sports, Travel, Gaming, People & Blogs, Comedy, Entertainment, News & Politics, Howto & Style, Education, Science & Tech, Nonprofits & Activism). Telegram needs its own topic set; the enum-schema/prompt-injection machinery around it is 🟢.
- 🟡 **Label normalization / alias map** (free-text/id → canonical class). Mechanism generic; aliases YouTube-specific.
- 🟡 **Reference-label source selection** (default: video-level `ai_label` in `yt_sl_videos`; or channel column; or expert table). Mechanism generic; default source YouTube-specific.
- 🟢 **Video→channel reference aggregation** (majority vote with thresholds: ≥3 labeled videos, ≥0.50 agreement; deterministic tiebreak). → maps to message-level → channel-level.
- 🟢 **Reference coverage summary** (n_channels, mean agreement per class).
- 🟡 **Per-channel prompt assembly**: channel name + description + detected language + recent-videos block (recency-ranked, capped) → `yt_category_llm_prompt_inputs`. "Recent videos" → "recent messages/posts."
- 🟢 **Language-stratified deterministic sampling** (4 run modes: labeled_validation / unlabeled_pilot / full_unlabeled / all_channels; stratify by detected-language × reference-category; `sha2(seed‖channel_id)` order). Requires a Telegram LID table upstream.
- 🟢 **Model bake-off roster**: 3 providers × 2 size tiers (frontier vs small) — OpenAI gpt-5.5/gpt-5-nano, Anthropic opus-4-7/haiku-4-5, Gemini 3.1-pro/flash-lite.
- 🟢 **Provider-specific JSONL request formatting** + optional batch submission + result parsing/normalization (enum-validated category, confidence clamp, ambiguous flag).
- **Evaluation metrics (the analyses to reproduce):**
  - 🟢 **Coverage & validity rates** per model (valid-prediction rate, parse-error rate, mean confidence, ambiguous count).
  - 🟢 **Accuracy vs reference** per model.
  - 🟢 **Macro-F1 / macro-precision / macro-recall** per model on full model×class grid (unpredicted classes count as F1=0).
  - 🟢 **Language-stratified accuracy** per model × detected language.
  - 🟢 **Pairwise inter-model agreement** (does the small model match the frontier model?).
  - 🟢 **Reported-confidence summary**.
- 🟢 **Multi-model consensus label** (majority vote across valid predictions; tiebreak on confidence then id).
- 🟢 **Decision gate** (README): do not run full-corpus until high reference agreement, strong macro-F1, stable cross-language performance, low parse-error, high small-vs-frontier agreement; else fall back to teacher-student distillation.

---

## 5. Core attention / audience manuscript analysis — Notebook 10

Paper 1, "Attention on YouTube." Central metric = **weekly views** = elapsed-day-normalized
change in lifetime views between two snapshots, `(views_t − views_{t−k}) / k × 7`. This metric
and most inequality/composition analyses port directly to Telegram view counts.

### Corpus / panel engineering
- 🟢 **Anchor snapshot selection** (completeness-guarded: latest partition with ≥90% of max-partition row count; prior = complete partition nearest current−7d). Table `attention_anchor_snapshot_coverage`.
- 🟢 **Weekly-views panel + entry/exit status** (snapshot differencing; `is_new_this_week`; negative-delta policy; dedupe; universe = subscribers ≥10k "Top of the Ocean"). Table `attention_measurability_status`.
- 🟡 **`channel_master` join**: language label (🟢, parallel LID pipeline) + native **YouTube `topic_categories`** (🔴, Wikipedia-derived — needs Telegram genre source) + coverage fractions.
- 🟢 **Traffic-block assignment**: ~20 equal-weekly-view-mass blocks (~5% each) via log-binning; observed/design/bounded tiers.
- 🔴 **Video-level frame** for format/production: Shorts (≤180s) vs Long-form classification + lookback windowing. Format axis is YouTube-only; the post-level snapshot framework is reusable.

### Descriptive distributions / proxy analyses
- 🟡 **Figure 1 — Discovery saturates**: new channels per crawl batch (peak-normalized) + high-subscriber head saturation. Idea generic if Telegram discovery is batch-based; the crawl tables are YouTube-collection-specific.
- 🟢 **Figure 3 — Subscribers are a noisy proxy for attention**: weekly-views p10/p50/p90 by log-subscriber bin; views-per-subscriber dispersion; inactive share by bin; Pearson r of log(subs) vs log(weekly views). Maps directly (members vs message views).

### Concentration / inequality
- 🟢 **Figure 4 + Table 1 — Threshold capture**: cumulative view-capture curve; channels & view share at subscriber thresholds 1k/10k/100k/1M; view share per ~5% block; tier mass.
- 🟢 **ED Fig. 3 — Lorenz / Gini / top-k concentration**: Lorenz curve, Gini coefficient (trapezoidal), top-k view shares at 0.1/0.4/1/5/10%. The canonical inequality battery — fully portable.

### Composition / language / category
- 🟡 **Figure 2 — Map of public YouTube**: language→category→channel treemap of weekly views; category composition across traffic blocks; per-language category composition + **Jensen-Shannon divergence** ("one platform or many"). Language composition + JSD are 🟢; the category axis is 🔴.
- 🟢 **Figure 5 (alt) — Language rank vs engagement & speaker population**: per-language weekly views, channel counts, mapped speaker population (ISO-639-3 lookup), rank-size log-log plots, views-per-capita.

### Growth / dynamics / age
- 🟢 **Figure 5a — Age structure by traffic block**: founding-year quartiles by block ("top channels are older"). Concept ports if a channel creation date exists; currently inert (no platform-wide creation date even for YouTube).

### Production / supply-demand (format axis)
- 🔴/🟢 **Figure 6 — Production vs attention by format**: supply-demand (median weekly views vs median uploads by format); production intensity per channel by block × format; format mix of recent-upload views. Shorts/long-form split is 🔴; the general "production/post intensity vs attention rank" idea is 🟢.
- 🟡 **ED Fig. 6 — Upload-age view distribution**: cumulative lifetime views by upload age in weeks per format. View-accrual-by-age calibration is generic; format split YouTube-only.

### Robustness battery
- 🟢 **Robustness summary**: R1 negative-delta-policy sensitivity (top-1% share), R3 suspicion-flag exclusion, R4 language-confidence gate coverage, R5 attention-window (weekly vs lifetime), Pearson-vs-diagnostics-Spearman cross-check. Method generic; some YT diagnostics tables specific.
- 🟢 **R7 — Category-missingness bounds**: per-category view share under lower / MAR / adversarial-upper assumptions about the ~20% uncategorized mass. Bounding technique generic; the instance is YouTube category coverage.

### Reproducibility scaffolding (reuse verbatim)
- 🟢 **Run manifest** (params, snapshot dates, coverage, headline numbers, checksums, degradation warnings).
- 🟢 **Export choke-point** (`export_table`: Delta + CSV, row-count cap, small-cell suppression <5).
- 🟢 **Figure design system** (Nature/Science spec, Okabe-Ito palette, 600 DPI).

---

## Porting cheat-sheet

**Port directly to Telegram (🟢 — corpus-agnostic):**
- Whole LID methodology: deterministic dedup/sampling, segment validity, dual fastText models, weighted channel voting, tiered consensus, mixed-language screen/credible, high-risk-tail flagging, stratified validation sampling, ablation-without-reinference, acceptance checks.
- Subscriber-cohort design (top-100k vs random band, member-count based).
- LLM language panel end to end (routing, batch plumbing, majority-vote reconciliation, blind-audit error estimate, provenance rules).
- Category bake-off machinery & all evaluation metrics (coverage/validity, accuracy, macro-F1 on full grid, language-stratified accuracy, pairwise agreement, consensus vote, decision gate) — everything except the taxonomy.
- Attention metric (weekly views from snapshot deltas), snapshot completeness selection, entry/exit panel, traffic blocks, subscriber-proxy dispersion, threshold capture + Table 1, Lorenz/Gini/top-k, language composition + JSD, language-rank vs speaker population, robustness sweeps, missingness bounds, all reproducibility scaffolding.

**Remap fields/taxonomy then port (🟡):**
- LID segment types & weights → Telegram fields (channel name, bio/about, message text); drop video titles/tags.
- LLM panel & category prompts → same field remap.
- Recall-audit template (Hindi/Indic) → whichever languages are under-detected on Telegram.
- Discovery-saturation figure if Telegram crawl is batch-structured.

**YouTube-only — needs a Telegram-native substitute or is dropped (🔴):**
- **Category/topic taxonomy** (the 15-class set and the manuscript `topic_categories` axis) — design a Telegram topic taxonomy; reuse all surrounding machinery.
- Declared-language confusion analysis (`defaultLanguage`) — no Telegram equivalent.
- Shorts vs long-form format axis (Fig 6, ED Fig 6, video frame) — needs a Telegram-native content-type axis (e.g. text vs media vs forwarded), if any.
- Source write-back into `yt_sl_channels`.

**Telegram-specific analyses likely to ADD (not in the YouTube code):**
- Forwarding / cross-posting network structure (no YouTube analogue).
- Message-level engagement (forwards, reactions, replies) and channel-to-channel reference graphs.
- A Telegram content-type axis to replace the Shorts/long-form format analyses.
