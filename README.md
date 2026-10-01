# telegram-descriptive

Descriptive analysis of high-reach public Telegram channels/groups, ported from
the methodology of the YouTube descriptive project and grounded in a live probe
of the Telegram Databricks environment (`prod_tads.telegram*`).

## Goals

The project supports four related outputs:

1. **A defensible Telegram "Top-of-the-Ocean" (TOO) sample frame** — high-reach
   public channels/groups with quantified subscriber/member (and, if selected,
   view) coverage.
2. **A descriptive analysis corpus** — post/message- and channel-level tables for
   language, topic, content-type, engagement, and network analysis.
3. **A methods package** — diagnostics documenting crawl behavior, eligibility,
   coverage, denominator estimation, uncertainty, and sensitivity.
4. **A reusable research resource** — stable gold tables and exports so later
   teams can compare their Telegram datasets to the discovered population and the
   TOO sample.

Non-goal for v1: no claims of statistical representativeness. The TOO is a
high-reach curated sample with quantified coverage of a reachable public
population, not a probability sample.

## Data environment

- Catalog/schemas: `prod_tads.telegram`, `prod_tads.telegram_random_walk`,
  `prod_tads.telegram_too` (mirrors the YouTube layout).
- Scale: ~29M posts across ~1,662 channels; precomputed 1024-d post embeddings,
  `detected_language`, repost/reply/quote linkage, hashtags, OCR/transcript text,
  and an enriched `subsample_items` table already exist.
- Known gap: random-walk **crawl lineage** (walk events, edge lists, chains,
  exposure tables) is not cleanly materialized yet, so population/coverage
  estimation is currently conditional. See the data-resources doc and the plan's
  "Gaps" section.

## Layout

```
docs/        project plan, data-resource context, analysis inventories, data contracts
src/         reusable data contracts, estimators, plots, exports (package modules)
scripts/     metadata/probe utilities (e.g. telegram_databricks_resource_probe.py)
notebooks/   orchestration + inspection only; heavy logic lives in src/
jobs/        Databricks workflow bundle resources
tests/       local tests for contracts, estimators, aggregation, and helpers
```

Design rule: notebooks orchestrate and inspect; shared code in `src/` implements
reusable data contracts, estimators, plots, and exports. Avoid one large
do-everything notebook.

## Current implementation status

This repository contains a runnable Databricks workflow implementation. The
notebooks are thin entry points over `telegram_descriptive.pipeline.spark_stages`,
which performs source reads, canonical silver-table construction, estimator
orchestration, gold-frame builds, descriptive summaries, network extraction,
robustness rows, validation/gap rows, and reporting manifests.

The notebooks default to `execution_mode=manifest_only`, which performs no
source reads or writes. To run the workflow end to end in Databricks, set:

```text
execution_mode=smoke  # bounded development run
execution_mode=core   # full table run
write_outputs=true
run_id=<stable run identifier>
```

The random-walk population-estimation pillar is explicitly gated: if exposure
and validation lineage tables are unavailable, the workflow writes no-claim gap
rows rather than fabricating representativeness or coverage estimates.

## Start here

- `docs/telegram_descriptive_analysis_plan.md` — full sequenced plan and milestones.
- `docs/data_contracts.md` — planned silver/gold table contracts.
- `docs/methods_tail_estimator.md` — rank-tail denominator implementation notes.
- `docs/methods_random_walk_crawl.md` — crawl lineage requirements and current gap.
- `docs/methods_language_detection.md` — Telegram LID segmentation and aggregation plan.
- `docs/methods_topic_classification.md` — Telegram-native topic taxonomy.
- `docs/README_telegram_data_resources.md` — schema/table/variable orientation map.
- `docs/AGENT_TELEGRAM_DATA_CONTEXT.md` — context for coding agents.
- `docs/databricks_telegram_resources.agent.json` — machine-readable schema manifest.

## Local verification

```bash
python -m pytest
```

The tests run without Databricks access. Databricks notebooks default to
`execution_mode=manifest_only` and should only perform table scans when run with
explicit smoke/core/full parameters.

## Dated live analysis

- **2026-09-29:** [Initial read-only crawl-9 analysis](docs/initial_analysis_2026-09-29.md).
  Queries against `qa_catalog.telegram_link_exposure_9` reconcile the channel
  totals, audit lineage, and produce subscriber accumulation curves plus
  exploratory Chao2/jackknife and saturation diagnostics. Formal population
  inference remains gated by sampling-unit, burn-in, lookback, and metric issues
  documented in the report. Existing estimator defaults were not changed.
- **2026-09-29 follow-up:** [Subscriber saturation across crawls 3–9](docs/saturation_crawls3_to9_2026-09-29.md).
  Globally deduplicated discovery curves across 6.895 million valid exposures,
  with pre-crawl-3 inventory offsets and a companion plot of each crawl's endpoint.
- **2026-09-29 follow-up:** [Crawl-9 moving discovery rates](docs/crawl9_moving_discovery_rates_2026-09-29.md).
  Linear plots of discoveries per million valid exposures, using a narrow 100k
  moving window and comparing subscriber thresholds within crawl 9 alone.

- **2026-09-29 smoothing update:** The crawl-9 moving-rate figures now default to
  a 250k exposure window, following the request for moderately more smoothing;
  the original 100k figures remain available.

- **2026-09-30:** [Subscriber size and capture/recapture in crawl 9](docs/crawl9_capture_by_subscribers_2026-09-30.md).
  Disjoint size bands, channel-level rank correlations, and source-exclusion
  sensitivity distinguish previously known channels from newly registered ones.
  The same frozen crawl-9 snapshot is used, with linear y-axes throughout.

- **2026-09-30 network visualization:** [Interactive undirected atlas](outputs/channel_graph_2026-09-30/visualization/undirected_atlas.html),
  [graph overview](outputs/channel_graph_2026-09-30/visualization/undirected_graph.png),
  and [adjacency density](outputs/channel_graph_2026-09-30/visualization/undirected_adjacency.png).
  The full observed graph contains 1,070,996 handle nodes and 3,524,298 unique
  undirected links, with no validation filter. The overview aggregates the
  main component into 824 exploratory Leiden communities; the matrix accounts
  for every original edge. [Methods and research](outputs/channel_graph_2026-09-30/visualization/visualization_methods.txt)
  include three-seed diagnostics and the two stopped full-node layout attempts.

- **2026-09-30 invalid-node correction:** [Corrected undirected atlas](outputs/channel_graph_filtered_2026-09-30/visualization/undirected_atlas.html)
  supersedes the unfiltered map for eligible-channel analysis. Explicit invalid
  records remove 540,063 nodes and 582,793 undirected links, leaving 530,933
  nodes and 2,941,505 links. Unknown validation and temporary deferrals remain
  eligible. [Audit and before/after source counts](outputs/channel_graph_filtered_2026-09-30/invalid_channel_audit.txt)
  distinguish invalid targets from still-eligible extreme-link sources.
  Live snapshot checks and independent SQL totals are preserved; the original
  unfiltered artifacts remain available for comparison.

- **2026-09-30 source-function investigation:** [Four extreme-link sources](outputs/channel_authenticity_audit_2026-09-30/investigation.txt)
  comprise two username-market event feeds, a student classifieds board, and a
  Telegram directory. Technical channel validation does not resolve these link
  meanings. Removing the two username feeds in a sensitivity calculation removes
  223,681 undirected edges and newly isolates 129,979 other nodes. Dated public
  evidence, read-only queries, and reproducible counts are preserved; this audit
  does not change the graph's exclusion policy or certify audience authenticity.

- **2026-09-30 outbound-link denominator and process audit:** [Full process audit](outputs/outbound_link_process_audit_2026-09-30/process_audit.txt)
  verifies that 3.86% is observed-source coverage of the original endpoint-defined
  graph, not link prevalence among completely scanned channels. Among eligible
  registry handles with positive processing counters, 74.16% have original
  outgoing edges and 69.42% retain edges after validation filtering; complete
  lookback scans remain unverified. The audit documents inspected code, exact
  visit/exposure reconciliation, missing collector/configuration access, and
  the distinction between confirmed behavior, measurements, and assumptions.

- **2026-09-30 independent-audit revision:** [Entity-level channel atlas](outputs/crawled_channel_graph_v2_2026-09-30/visualization/crawled_channels_atlas.html)
  resolves 73,786 crawled/visited handles to 72,326 snapshot entities with 820,041
  undirected ties. [Audit response](outputs/crawled_channel_graph_v2_2026-09-30/revision/audit_response.txt)
  documents alias merging, corrected pixel coverage and floating-point edge
  accumulation, preserved community-center geometry, denominator sensitivity,
  dense-block disclosure, and clean/cache reproducibility checks. The original
  atlas and audit remain available. Historical identity, complete lookback scans,
  crawl-5–7 registry coverage, and fresh SQL reconciliation remain unverified.

- **2026-09-30 overlap and subscriber-filter revision:** [Atlas v3](outputs/crawled_channel_graph_v3_2026-09-30/visualization/crawled_channels_atlas.html)
  adds circle-aware overlap removal, protection against collisions during zoom
  and resizing, and a minimum-subscriber slider with exact input. Independent
  checks find zero circle intersections in the resulting geometry. The
  [methods and measured distortion](outputs/crawled_channel_graph_v3_2026-09-30/visualization/methods.txt)
  report the tradeoff in spatial fidelity; graph relationships, weights and
  communities are unchanged. Previous versions remain available.


## 2026-09-30 — community descriptions and atlas v4

Added provisional semantic descriptions to the unchanged v3 graph and geometry.
The user selected the union of the top 50 communities by node count OR summed
subscribers: 66 groups, 51,252 channels, and 87.9% of the graph subscriber sum
(not unique people). Reports and the community menu are ordered by descending
subscriber sum; original partition IDs remain fixed.

The frozen samples contain 1,847 entities: ten largest plus twenty disjoint
hash-random others per group, or a census for smaller groups. Three GPT-6.1-sol
agents at low effort reviewed them. After the user's efficiency amendment, 44
groups used metadata first with targeted and deterministic post audits; 22
groups retained detailed review. Of the 1,187 staged annotations, 699 used
metadata and 488 inspected posts. No quality-equivalence claim is made.

Root chose every final label and recorded its rationale, retaining the agent
proposal and per-channel evidence. Usable subject/function evidence exists for
1,752/1,847 samples (626/629 top and 1,126/1,218 random). The seven low-confidence
groups remain explicitly mixed or evidence-limited. Current public previews do
not verify historical identities or the original lookback corpus; these are
model-assisted descriptions, not human-validated labels for every member.

Outputs: `outputs/community_labels_2026-09-30/` contains protocol amendments,
rankings, sample plan, cached HTML/text, 66 reports, root decisions and checks.
`outputs/crawled_channel_graph_v4_2026-09-30/` contains the labeled atlas,
searchable `visualization/community_reports.html`, CSV export and provenance.
Local preview: `http://127.0.0.1:65262/crawled_channels_atlas.html`. The separate
label sidecar is fingerprinted to the exact reference partition and is hidden
for alternative resolutions/denominators. The prior v3 artifact is preserved.

Independent checks confirm the selected union, exact samples, complete review
coverage, source hashes and byte-identical graph/layout files. Browser checks
passed at DPR 1 and 2: menu order, report access, node-to-report links, alternative
partition suppression, subscriber filtering, fixed positions, saved views,
mobile width and collision suppression. Ten displayed overview community labels
had zero pairwise overlaps or intersections with tested circles of radius at
least one CSS pixel. Subpixel marks are excluded from label collision avoidance.

The graph-visualization skill now includes research-backed community-labeling
procedures. Detailed methods, direct research links, review-depth limitations,
root source checks and reproduction commands accompany the artifacts.

## 2026-09-30 — stable community navigation in atlas v5

[Atlas v5](outputs/crawled_channel_graph_v5_2026-09-30/visualization/crawled_channels_atlas.html)
fixes the unstable v4 community-name UI. The v4 renderer recomputed visible
importance, anchors and callout positions on each frame; its still-frame tests
missed the resulting pan/zoom instability reported by the user. All prior
versions and research results remain available.

The new UI uses fixed world-space names, full-community subscriber priorities,
11-pixel single-line aliases and predetermined zoom activation. A persistent
ranked list highlights exact community members without moving the camera;
Locate is explicit. Full descriptions and evidence remain available on demand.
The subscriber filter is prominent; secondary controls are collapsed. These
presentation changes preserve all 35 checked graph/layout/semantic-report/style
files byte for byte, including all 72,326 entities and 820,041 undirected ties.

Actual drag and zoom tests passed at desktop DPR 1/2 and mobile DPR 2. Label
translation error was below 3e-13 CSS pixels; active ranges were monotonic and
had zero text-text collisions at 12 tested zoom levels. Desktop overview shows
the eight largest communities; mobile starts with three. Selection, keyboard
operation, saved views, reports, filters and responsive reflow passed. Node-label
intersections can occur at intermediate zoom; stable positions take priority
over avoiding every small circle. Strict node avoidance was rejected during
development because it deferred useful labels to extreme zoom.

[Revision methods and limitations](outputs/crawled_channel_graph_v5_2026-09-30/revision/label_ui_revision.txt)
record the research, placement policy, measured intersections and reproduction
commands. Motion verification and screenshots are in `visualization/`. The
network-visualization skill now covers temporal consistency, stable priorities,
progressive disclosure and motion tests. Local preview:
`http://127.0.0.1:65263/crawled_channels_atlas.html`.

### 2026-09-30 — community label colors

Updated v5 map names and ranked sidebar names to use the exact community node
palette color, including the selected community. The dark text halo and fixed
placement remain. Browser inspection verified all eight overview names and the
selected name against the node palette; screenshot and color checks are in the
v5 output. Placement remains an open user concern; this change addresses the
requested color correspondence.

## 2026-09-30 — hull-attached community labels in atlas v6

[Atlas v6](outputs/crawled_channel_graph_v6_2026-09-30/visualization/crawled_channels_atlas.html)
corrects the remaining zoom-detachment problem in v5. The user identified that
label placement was still poor: the old text-center offset was in world units,
so its screen-space separation grew with zoom even though the motion was smooth.

Names now attach at their near edge/corner to left/right-facing ports on the
full community convex hull. Text extends away from the community, with matching
node colors and a 6–8 CSS pixel gap that does not grow with zoom. Candidate ports
are evaluated for whitespace across eight zoom scales; interval checks prevent
future text collisions. Responsive plans retain stable anchors during pan,
zoom and filtering. Graph geometry and all 35 checked graph/layout/semantic/style
files are byte-identical to v5.

At four viewport/DPR configurations, 379 scale checks per configuration verified
hull support, the correct attachment side, bounded pixel gaps, no text-text
collisions and no clipped overview names. UI/navigation/filter/save-view checks
also passed. Some label rectangles intersect small node marks; avoiding every
mark is not a reason to detach a label from its community. A convex hull may
contain empty space and is not a substantive boundary. Prior results and v5
artifacts are retained; its earlier center-transform test did not detect this
specific anchoring failure.

[Methods and measurements](outputs/crawled_channel_graph_v6_2026-09-30/revision/hull_label_revision.txt)
include research sources, tradeoffs, source snapshots and reproduction commands.
Local preview: `http://127.0.0.1:65264/crawled_channels_atlas.html`.

## 2026-10-01 — member-anchored community names in atlas v7

[Atlas v7](outputs/crawled_channel_graph_v7_2026-10-01/visualization/crawled_channels_atlas.html)
fixes the problems an [independent review of v6](outputs/crawled_channel_graph_v6_2026-09-30/revision/opus_review/OPUS_REVIEW.md)
measured: hull-edge names often sat on or beside other communities, and their
distance to their own channels still grew with zoom along long hull edges.

Each name now attaches to one real, displayed member on its community's outer
boundary, a fixed 6 px beyond that channel's rendered circle at every zoom.
Candidates are scored across their zoom range for other communities' marks
under or near the text; names that cannot be placed cleanly activate later or
stay in the list instead of being drawn on another community. Neighbouring
communities now get clearly different colors. Names are never drawn truncated
or under map controls; Locate frames the name as well as the members; small
resizes no longer re-plan; filters and size changes re-anchor names to
displayed channels.

Compared with v6 on the review's metrics, foreign marks under names fell from
377 to 2 (desktop 4×) and from 1,126 to 3 (mobile 8×), and no name is more than
6 px from its own marks (v6: up to 2,118 px). The tradeoff is fewer names at
intermediate zoom (desktop 2.8×: 38 vs 50). Graph, layout and label data are
byte-identical to v6.

[Methods](outputs/crawled_channel_graph_v7_2026-10-01/visualization/methods.txt),
[finding-by-finding response](outputs/crawled_channel_graph_v7_2026-10-01/revision/review_response.txt)
and [verification results](outputs/crawled_channel_graph_v7_2026-10-01/visualization/member_labels_verification.json)
include the measurements, tradeoffs and reproduction commands.

## 2026-10-01 — v7 corrections in atlas v8

[Atlas v8](outputs/crawled_channel_graph_v8_2026-10-01/visualization/crawled_channels_atlas.html)
keeps v7's names, placements and colors and fixes three problems found by an
[independent review of v7](outputs/crawled_channel_graph_v7_2026-10-01/revision/codex_review_2026-10-01/REVIEW.txt):
temporary "selected channel + neighbors" focus combined with a resize could
erase every community name (even after Reset); on phones, Locate positioned the
name correctly inside the map but could leave the map scrolled out of view; and
the archived v6/v7 comparison script did not run on v6. Names are also now
described as boundary-preferred rather than guaranteed to sit on the outer edge.

The verifier now reproduces the focus → resize → Clear → Reset sequence and runs
Locate through the real controls for all 66 groups, asserting the name ends up
inside the browser viewport (66/66 desktop, 65/66 mobile; the exception is the
one name not placed on mobile). A corrected, version-independent audit confirms
the v7 gains for the same communities (desktop 4×: 176 → 2 foreign marks under
names; mobile 8×: 224 → 3). All data inputs are byte-identical to v7.

[Methods and corrections](outputs/crawled_channel_graph_v8_2026-10-01/visualization/methods.txt) ·
[review response](outputs/crawled_channel_graph_v8_2026-10-01/revision/review_response.txt) ·
[comparison data](outputs/crawled_channel_graph_v8_2026-10-01/revision/association_comparison_v6_v7_v8.json)

## 2026-10-01 — weight-proportional ties and linked communities in atlas v9

[Atlas v9](outputs/crawled_channel_graph_v9_2026-10-01/visualization/crawled_channels_atlas.html)
fixes the uninformative grey tie wash. A [review](outputs/tie_layer_review_2026-10-01/)
of the [tie-layer research](outputs/tie_layer_research_2026-10-01/RESEARCH_AND_PROPOSAL.txt)
found that tie ink followed line length rather than strength: long weak links
painted the whole map while the strongest 1% of ties (48% of weight) got 1.4% of
the ink. Each tie's ink is now proportional to its weight, with brightness on a
fixed log scale calibrated once per window size. Near-maximum tie pixels at the
overview fall from about 55–63% to under 1%, and halos and corridors become
visible. Strong individual ties are almost all short; distant groups are linked
mainly by many weak ties.

Selecting a channel or community draws its ties in a separate, brighter layer
(own brightness scale, lighter colour, partial length compensation) so long-range connections remain
visible. A community's panel lists its linked communities with weight, share,
direction and affinity; clicking one shows only that pair's ties. Node positions,
sizes, labels and colors are unchanged; data inputs are byte-identical to v8.

[Methods](outputs/crawled_channel_graph_v9_2026-10-01/visualization/methods.txt) ·
[tie verification](outputs/crawled_channel_graph_v9_2026-10-01/visualization/tie_layer_verification.json)
