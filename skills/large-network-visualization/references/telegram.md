# Telegram dataset context, 2026-09-30

The first section records the original handle-level analysis. Use the revision below for the current atlas.

Repository: /Users/hindman/Documents/GitHub/telegram-descriptive.
The current collector implementation and historical API errors are not available.
Do not infer exact validation logic from reason names. "Eligible" refers to the
recorded registry policy, not verified authenticity or a complete lookback scan.

Frozen qa_catalog.telegram_link_exposure_9 versions:
seed_channels=20, invalid_channels=18, source_visit_records=18,
link_exposure_records=28, edge_records=22. The schema contains earlier crawls too.
The registry snapshot's latest export was September 28, 2026.

The verified graph cohort contains 73,786 eligible channels with a nonnull
last_crawled_at OR a recorded source visit. It includes one visit-only handle.
The requested approximate 130k was not supported by the available registries;
older crawl3/4/8 markers add no currently eligible channels beyond this set.
Re-query if a different cohort or source is supplied rather than padding counts.

Inputs under outputs/channel_graph_filtered_2026-09-30/graph preserve the larger
eligible graph, needed for full outgoing-degree denominators. The induced cohort
has 826,106 unique undirected pairs, 1,111,649 directed pairs, and 5,957 isolates.
No subscriber counts are null; 437 are recorded zero and require special markers.
Stored subscriber counts are not guaranteed current or measured at link time.

The derived filter excludes invalidated registry rows, is_channel=false, and
invalid-channel reasons other than deferred_giant_channel. Error and no_count
reasons are unresolved rather than proven type failures. The 2026-09-30 invalid
endpoint audit documents this limitation. The export stores username handles,
so historical reassignment can mix entities if a stable chat ID is unavailable.

For this visualization use distinct directed pairs, source-fractional weights
with alpha=1, symmetrized by summation. Full valid target count includes destinations
outside the displayed cohort. Preserve raw evidence columns for later improvements.
Do not interpret repeated visits/exposures as post-level mention intensity.

## September 30 audit correction: snapshot entity atlas v2

The 73,786 cohort handles resolve to 72,326 snapshot entities (72,325 chat IDs plus one handle fallback), with 820,041 undirected ties. There are 1,037 multi-handle entities and 301 with conflicting subscriber observations. Choose one observed row by newest HTTP validation timestamp, then crawl timestamp and handle; this is a declared representative policy, not a verified measurement-time rule. Preserve all alias observations and count ranges.

Use outputs/crawled_channel_graph_v2_2026-09-30 for current results, retaining the original and independent audit. Resolve full-reference targets by known ID before degree normalization; retain eligible-target and all-observed-target variants. The max-core block remains 1,055 entities and contains 507,569 internal ties; report its disproportionate contribution and do not infer authenticity or coordination from density alone.

Do not claim all historical registries were reconciled: crawl 5–7 access and fresh SQL reconciliation remain blocked by the Databricks source-IP ACL. The September 30 retry is recorded in the v2 results directory. The original count is a verified available cohort, not proof that 130k channels were never crawled.

The revised renderer uses analytic circle/pixel coverage, a tested RGBA32F edge accumulator, real rendered tie swatches, log core colors, attained-value core slider, and optional dim zero markers. Layout uses independent seeded calls with fingerprinted caches. Community centers are not repacked; quotient attraction is log1p(weight/median), local weights are median-normalized, and local layouts are scaled to available center spacing. Blob size is not an analytical measurement.

## September 30 overlap revision (v3)

The v3 atlas adds circle-aware overlap removal, a minimum-subscriber slider and exact input, default overlap protection across resizing/zoom/size changes, and suppressed labels that would cover visible circles. Use outputs/crawled_channel_graph_v3_2026-09-30. The graph, subscriber observations and community memberships are unchanged from v2; display spacing now depends on subscriber radii. Keep the original graph coordinates for comparison. See references/overlap.md for the research and measured tradeoffs.
