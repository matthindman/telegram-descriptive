# Saturation across Telegram crawls 3–9

**2026-09-29 follow-up.** The requested range is crawl 3 onward. This extends
the [initial crawl-9 analysis](initial_analysis_2026-09-29.md) while preserving
its data snapshots and subscriber thresholds. All Databricks work was read-only.

## Observed curves

![Subscriber saturation across crawls 3–9](../outputs/crawls3_to9_2026-09-29/analysis/subscriber_saturation_crawls3_to9.png)

The seven selected crawls contribute **6,895,115 valid link exposures** from
August 13 through September 28, 2026. They expose **445,747 distinct handles
validated as public at least once**, before current-usability and size filtering.
The latest schema contains this historical data; older schema copies were not
unioned into it.

The large early increase comes from crawl 4. Subsequent discovery is slower per
valid exposure, but remains positive. Crawl 9 contributes 19,608 newly encountered
eligible handles with ≥1,000 subscribers, 3,844 with ≥10,000, 419 with ≥100,000,
and 22 with ≥1 million. The curves do not demonstrate closure or provide an
estimate of population completeness.

Because crawl lengths vary greatly, a companion view gives every crawl an
equally spaced endpoint. Its horizontal spacing is **not** proportional to effort.
Crawl 5 has only 793 valid exposures and is nearly invisible on the effort plot.

![Inventory after each crawl](../outputs/crawls3_to9_2026-09-29/analysis/crawl_end_inventory.png)

## Contributions, with repeated discoveries counted once

Counts below are discoveries beyond the frame known before crawl 3. Each handle
is attributed to its first valid exposure among crawls 3–9; this can differ from
its registry `crawl_id_added` tag. The subscriber thresholds are nested.

| Crawl | Valid exposures | New ≥1k | New ≥10k | New ≥100k | New ≥1m |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3 | 130,265 | 7,912 | 1,637 | 184 | 15 |
| 4 | 392,827 | 26,363 | 11,248 | 2,480 | 111 |
| 5 | 793 | 19 | 0 | 0 | 0 |
| 6 | 129,934 | 1,807 | 595 | 155 | 13 |
| 7 | 595,467 | 3,359 | 651 | 61 | 1 |
| 8 | 269,980 | 1,521 | 339 | 41 | 1 |
| 9 | 5,375,849 | 19,608 | 3,844 | 419 | 22 |
| **Total** | **6,895,115** | **60,589** | **18,314** | **3,340** | **163** |

| Subscribers ≥ | Known before crawl 3 | Subsequent discoveries | Curve endpoint | Current registry |
| --- | ---: | ---: | ---: | ---: |
| 1,000 | 109,921 | 60,589 | 170,510 | 170,512 |
| 10,000 | 28,930 | 18,314 | 47,244 | 47,244 |
| 100,000 | 3,563 | 3,340 | 6,903 | 6,903 |
| 1,000,000 | 293 | 163 | 456 | 456 |

The two-handle discrepancy at ≥1k is the same two unexposed registry additions
documented in the initial report. No synthetic exposure or discovery time was
assigned to them. At the descriptive ≥0 threshold, the curve contains 612,583
handles with known member counts versus 612,585 in the usable registry. Another
four usable registry handles have unknown member counts.

## Construction and limits

- The baseline includes usable registered handles inserted before
  **2026-08-13 00:36:12.229 UTC**, crawl 3's recorded start. Earlier crawls enter
  only through that baseline; they contribute no exposure effort to these plots.
- Usability is `is_channel=true`, no `invalidated_at`, and no matching handle in
  the invalid/deferred table. Both usability and `member_count` come from the
  fixed September export. The plots retrospectively classify channels by that
  snapshot; they do not reconstruct historical subscriber counts or status.
- Every valid exposure counts as effort, including repeat encounters and targets
  below the displayed size threshold. Within each run there are no duplicate
  `(batch_id,target_channel)` valid-exposure keys. Each eligible target contributes
  to discovery only once across all selected runs, and pre-frame handles never
  contribute a second time.
- Ordering is by `extracted_at`, `crawl_id`, `sequence_id`, `visit_id`, then
  `exposure_id`. Discovery counts are aggregated into 25,000-valid-exposure bins
  within each crawl, retaining each crawl's exact final partial bin. Displayed
  lines connect observed bin endpoints; they are not fitted saturation models.
- Deduplication is by handle. Incomplete stable chat IDs prevent complete entity
  deduplication, as described in the original analysis.
- Crawl 3 records `new_only`; crawls 4–9 record `all_valid`. Source-visit coverage,
  chain independence, lookback, and effort comparability remain unresolved across
  the full history. No pooled Chao2 or asymptotic fit was added, and existing
  estimator defaults and the original crawl-9 diagnostics were unchanged.

## Reproduction and validation

Source: `qa_catalog.telegram_link_exposure_9`, using Delta versions
`link_exposure_records=28`, `seed_channels=20`, `invalid_channels=18`;
the crawl start is from the earlier `crawl_runs=18` audit. The analysis uses
`matt.hindman@researchaccelerator.org` and the existing Tiny Warehouse.

Four selected-range SQL queries succeeded without truncated results. Checks
confirmed complete valid-exposure keys, zero within-run batch/target duplicates,
contiguous effort bins, and agreement between the curves and a separate
distinct-target/registry inventory query at all five saved thresholds. The
plotting script passed Ruff and compilation, and both PNG figures were inspected.

- [Read-only SQL batch](../outputs/crawls3_to9_2026-09-29/queries/01_crawls3_to9.json)
- [SQL results and statement provenance](../outputs/crawls3_to9_2026-09-29/results/)
- [Plotting script](../scripts/plot_crawls3_to9_readonly.py)
- [25k-exposure curve data](../outputs/crawls3_to9_2026-09-29/analysis/accumulation_bins.csv)
- [Per-crawl totals and discovery rates](../outputs/crawls3_to9_2026-09-29/analysis/crawl_endpoints.csv)
- [Frame reconciliation](../outputs/crawls3_to9_2026-09-29/analysis/frame_inventory.csv)
- [Machine-readable summary](../outputs/crawls3_to9_2026-09-29/analysis/summary.json)
- [Saturation figure, PDF](../outputs/crawls3_to9_2026-09-29/analysis/subscriber_saturation_crawls3_to9.pdf)
- [Saturation figure, SVG](../outputs/crawls3_to9_2026-09-29/analysis/subscriber_saturation_crawls3_to9.svg)

Rebuild the local figures without further Databricks queries:

```bash
MPLCONFIGDIR=/private/tmp/telegram-mpl python3 scripts/plot_crawls3_to9_readonly.py outputs/crawls3_to9_2026-09-29
```

The preceding four-query exploration of all retained runs remains under
`outputs/all_crawls_2026-09-29/` as provenance. The final figures and claims in
this follow-up use only the user-selected range 3–9.

## 2026-09-29 follow-up: logarithmic y axes

Added log-y versions using the same counts and linear exposure axis. Each panel
uses the same multiplicative y-range relative to its starting inventory, so an
equal percentage increase occupies the same vertical distance across panels.
Tick labels show ordinary counts at their logarithmic positions. The original
linear figures remain available. No further database queries were needed.

![Log-y saturation across crawls 3–9](../outputs/crawls3_to9_2026-09-29/analysis/subscriber_saturation_crawls3_to9_log_y.png)

- [Log-y saturation PDF](../outputs/crawls3_to9_2026-09-29/analysis/subscriber_saturation_crawls3_to9_log_y.pdf)
- [Log-y saturation SVG](../outputs/crawls3_to9_2026-09-29/analysis/subscriber_saturation_crawls3_to9_log_y.svg)
- [Log-y crawl endpoints](../outputs/crawls3_to9_2026-09-29/analysis/crawl_end_inventory_log_y.png)

Both rendered log-y figures were visually inspected. The plotting script's
existing numerical reconciliation checks, Ruff, and compilation passed.

## 2026-09-29 clarification of interpretation

The flattening is evidence of diminishing discovery returns and is consistent
with approaching saturation. The sparse 22 additions in the million-subscriber
group do not invalidate that evidence. What remains unresolved is the rate of
further decline and the size of the unseen population. See the [dated
clarification in the initial report](initial_analysis_2026-09-29.md#2026-09-29-clarification-flattening-versus-completeness)
for the checked rates and the distinction from demonstrated completeness.

## 2026-09-29 display preference and within-run follow-up

Linear axes are again the default; `--include-log-variants` enables the optional
log figures when rebuilding. The next requested analysis focuses on differential
decline within crawl 9, avoiding the earlier runs' method differences. See
[the narrow moving-rate analysis](crawl9_moving_discovery_rates_2026-09-29.md).
