# Crawl 9: subscribers and capture / recapture

Analysis completed **2026-09-30**. This extends the [initial crawl-9 audit](initial_analysis_2026-09-29.md) using the **same frozen Delta versions**, covering 10–28 September 2026. It does not pool earlier crawls or refresh the snapshot. All remote statements were reads.

## Main finding

**Subscriber size is positively associated with capture and repeat capture among previously known channels at or above 1,000 subscribers, but it does not provide a universal detection model.** Capture rises from 23.5% in the 1k–<10k band to 37.3% in the ≥1m band. Conditional recapture rises from 65.5% to 85.2%, and mean recorded-chain incidence rises from 5.58 to 31.40. The medians rise from 2 to 5, showing that the means also reflect a heavy upper tail.

Among newly registered channels ≥1k, the channel-level rank association between subscribers and number of capturing chains is essentially zero (Spearman ρ = −0.013; 19,608 captured handles), versus +0.183 among previously known captured channels (39,816 handles). New-channel mean counts rise across the four broad upper bands, but that pattern does not translate into a monotonic relationship across individual channels; sparse large-channel observations and skew matter.

Very small channels form a distinct pattern: previously known 1–9 subscriber handles have a 94.3% conditional recapture fraction, and the 10–99 band averages 86.0 recorded chain IDs per captured handle. Pooling all positive subscriber counts gives a negative size–chain-count correlation among captured pre-existing handles (ρ = −0.494). This is why the complete size curve, the ≥1k comparison, and source exclusions are all reported.

![Subscriber size and capture/recapture](../outputs/crawl9_capture_size_2026-09-30/analysis/subscriber_capture_recapture.png)

## What the quantities mean

For each handle, let K be the number of distinct recorded `chain_id` values containing a valid crawl-9 exposure to that target. Multiple exposures to the same target within a chain count once.

- **Capture fraction:** handles with K ≥ 1 divided by all eligible handles registered before crawl 9, within the subscriber band. Uncaptured registered handles remain in this denominator.
- **Conditional recapture fraction:** handles with K ≥ 2 divided by handles with K ≥ 1. Equivalently, 1 − Q1/D, where Q1 counts handles captured in exactly one chain and D counts captured handles.
- **Repeat-capture frequency:** mean K among captured handles. Medians are included in the tables to reveal skew.

These are empirical fractions and frequencies over this crawl, not per-exposure probabilities or coverage of all Telegram. A target exposure is a discovered link; it does not require visiting or downloading that target's own channel. Recorded chains are used for consistency with the earlier Chao incidence audit; independence and equal effort have not been established.

The frame is reconstructed from handles registered before `2026-09-10 00:01:46.341 UTC`, retaining only those usable in the frozen export: `is_channel=true`, no `invalidated_at`, and no matching `invalid_channels` entry. Subscriber bands use **export-time `member_count`**, because exposure-time counts are missing. Thus this is not a historical subscriber-size measurement or an unconditioned historical inventory.

All bands are disjoint. The main figure uses linear y-axes and includes zero-subscriber handles. Four pre-existing handles with unknown size are omitted from size plots and retained in the exported data; one was captured. Known-size pre-existing inventory totals 505,279 handles, with 98,305 captured (19.46%). Newly registered known-size inventory totals 107,306, with 107,304 captured; the two unmatched handles have 6,160 and 9,440 subscribers. Their inclusion in the registry does not create valid exposures.

New-channel capture fractions are not plotted because registration during the crawl largely conditions on discovery. Their recapture measurements also differ in time available after first discovery; they are not exposure-opportunity-adjusted estimates.

## Previously known channels

Recapture percentages, means and medians below condition on being captured at least once.

| Subscribers | Pre-crawl inventory | Captured | Capture % | Recapture % | Mean chains | Median chains |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 8,267 | 321 | 3.9 | 94.4 | 38.56 | 59 |
| 1–9 | 140,320 | 34,639 | 24.7 | 94.3 | 43.92 | 60 |
| 10–99 | 68,000 | 7,108 | 10.5 | 81.4 | 85.99 | 60 |
| 100–999 | 137,790 | 16,421 | 11.9 | 60.1 | 5.29 | 2 |
| 1k–<10k | 107,502 | 25,246 | 23.5 | 65.5 | 5.58 | 2 |
| 10k–<100k | 36,916 | 12,314 | 33.4 | 73.1 | 10.02 | 3 |
| 100k–<1m | 6,050 | 2,094 | 34.6 | 77.7 | 20.00 | 5 |
| ≥1m | 434 | 162 | 37.3 | 85.2 | 31.40 | 5 |

The ≥1m versus 1k–<10k capture-fraction ratio is 1.59; conditional mean chain incidence is 5.63 times larger. The ≥1m recapture value is 138/162, with 24 single-chain handles. These are associations within the retained pre-crawl inventory.

## Newly registered channels

| Subscribers | Captured | Exactly one chain (Q1) | Recapture % | Mean chains | Median chains |
| --- | --- | --- | --- | --- | --- |
| 0 | 291 | 106 | 63.6 | 17.88 | 2 |
| 1–9 | 33,249 | 9,517 | 71.4 | 18.45 | 4 |
| 10–99 | 21,477 | 13,079 | 39.1 | 2.91 | 1 |
| 100–999 | 32,679 | 18,508 | 43.4 | 2.55 | 1 |
| 1k–<10k | 15,764 | 9,022 | 42.8 | 2.92 | 1 |
| 10k–<100k | 3,425 | 1,934 | 43.5 | 3.83 | 1 |
| 100k–<1m | 397 | 244 | 38.5 | 4.19 | 1 |
| ≥1m | 22 | 10 | 54.5 | 9.00 | 2 |

For the newly registered ≥1m group, 12 of 22 handles are recaptured, and 10 appear in only one recorded chain. The 54.5% figure therefore describes 22 observed handles; it is not a precise estimate for the unseen large-channel population. Lower and flatter discovery rates from the earlier analysis remain evidence of diminishing returns, while these recapture results address heterogeneity among observed handles.

## Channel-level associations

Spearman correlations use exact average ranks for ties, calculated inside Databricks from channel-level data. They are not correlations between the plotted bin means. A binary capture outcome has ranks affine to the binary values, so correlation with the subscriber rank yields the corresponding Spearman statistic. Capture ≥1 is constant in captured-only cohorts and its correlation is undefined (shown as a dash).

| Minimum subscribers | Cohort | Handles | ρ(size, chain count) | ρ(size, captured ≥1) | ρ(size, captured ≥2) |
| --- | --- | --- | --- | --- | --- |
| 1 | Newly registered, captured | 107,013 | -0.318 | — | -0.209 |
| 1 | Previously known, captured | 97,984 | -0.494 | — | -0.239 |
| 1 | Pre-crawl inventory, including uncaptured | 497,012 | +0.006 | +0.040 | -0.034 |
| 1,000 | Newly registered, captured | 19,608 | -0.013 | — | -0.015 |
| 1,000 | Previously known, captured | 39,816 | +0.183 | — | +0.105 |
| 1,000 | Pre-crawl inventory, including uncaptured | 150,902 | +0.141 | +0.127 | +0.133 |

In the full inventory, K includes zeros. In captured-only cohorts, K ≥ 1 by construction. The distinction explains why those correlations answer different questions. For example, among ≥1k pre-crawl handles, size has a +0.127 association with being captured at all and a +0.183 association with chain count conditional on capture. Neither is an estimate of a causal effect of subscribers.

No p-values or independent-binomial confidence intervals are asserted: the crawler creates shared-source and chain dependence, and these are descriptive results for a frozen crawl.

## Source sensitivity

![Source-exclusion sensitivity](../outputs/crawl9_capture_size_2026-09-30/analysis/subscriber_capture_source_sensitivity.png)

Deleting exposures from `fragment_monitor` and `lelang_username` is a sensitivity analysis of the recorded data, not a simulation of a crawler that never visited those sources. Pre-crawl inventory denominators remain unchanged, but conditional recapture denominators become the handles still captured after each exclusion.

- **Previously known 1–9 subscriber handles:** capture falls from 24.69% to 3.85%; conditional recapture falls from 94.34% to 46.38%. Removing `fragment_monitor` alone reduces mean chain count from 43.92 to 2.17, even though conditional recapture remains 93.72%. Thus frequent repetition and merely appearing in two chains are materially different summaries.
- **Previously known ≥1k handles:** the upward association across size bands persists after removing both sources. Conditional recapture is 64.60%, 72.14%, 76.68%, and 85.44% across the four upper bands, versus 65.45%, 73.12%, 77.70%, and 85.19% with all sources.
- **The 10–99 subscriber anomaly remains:** mean chain count among retained pre-existing captures is 95.17 after both exclusions (85.99 before), with 5,777 captured handles remaining. The two named sources therefore do not explain all extreme recurrence among small channels. The conditional mean can increase when exclusion removes less recurrent handles.
- **Newly registered ≥1m handles:** after excluding both sources, 16 remain captured, 6 recur in ≥2 chains (37.5%), and mean chain count is 1.75, versus 22 captured, 12 recaptured and mean 9.0 with all sources. This sparse group's repeat-capture summary is sensitive to where its links appear.

## Finer subscriber bins

![Half-decade subscriber bins](../outputs/crawl9_capture_size_2026-09-30/analysis/subscriber_capture_fine_bins.png)

This companion uses half-decade bins (a factor of √10 in subscriber count), with points at each cohort's median subscriber count. Only its **x-axis** is logarithmic; y-axes remain linear. Zero and unknown sizes cannot appear on this x-axis. Upper bins with few observations are labeled; the last pre-crawl inventory bin contains only nine handles, so its high capture fraction should not be generalized. Lines connect descriptive bin summaries and are not fitted smooth curves.

## Implication for the Chao analysis

Recapture behavior differs by subscriber size, registration cohort and link source. The pre-existing inventory's size relationship cannot simply be transferred to the newly discovered tail to estimate unseen channels. The observed Q1 counts above are directly relevant to the prior Chao2 diagnostics, but these plots do not themselves fit a population estimator or establish an upper bound. No registered estimator formula, sampling-unit rule or inference gate has been changed.

A useful next modeling step would separate subscriber-size effects from discovery timing, source concentration and comparable sampling effort. That is beyond this descriptive analysis; the new-cohort differences here remain unadjusted for those factors.

## Reproducibility and verification

Source: `qa_catalog.telegram_link_exposure_9`, filtering exposures to `crawl_id='telegram-link-exposure-9'` and `target_is_valid_public_channel=true`. Reads use `seed_channels VERSION AS OF 20`, `invalid_channels VERSION AS OF 18`, and `link_exposure_records VERSION AS OF 28`.

Three new read-only queries completed successfully:

| Query | Rows | Statement ID |
| --- | ---: | --- |
| size_band_capture | 51 | `01f1bc57-2177-1d4c-8796-7e5a21dfbafb` |
| fine_size_capture | 96 | `01f1bc57-2183-1a7d-81b7-c0371e892559` |
| subscriber_incidence_association | 6 | `01f1bc57-27c7-1f63-be0f-9ebffe862f1d` |

The initial connection attempt was denied by the workspace IP ACL before receiving statement IDs. Its failure records remain in `results/blocked_attempt/`; all three queries succeeded after the user restored connectivity. There is no remaining query-access blocker for this analysis.

The direct band counts reconcile exactly with the earlier audit's independently saved cumulative-threshold results, including both source exclusions. Finer bins reconstruct the direct bands exactly. All scenarios pass nonnegative count, cohort-bound and D−Q1 recapture checks. Rank-correlation cohort sizes match the band queries. Totals reconcile to 612,589 usable registry handles and 205,610 captured handles including unknown size. Successful/untruncated result checks, Ruff, Python compilation and visual inspection of all three figures passed.

SQL and raw results are in `outputs/crawl9_capture_size_2026-09-30/queries/` and `results/`. The seven input result files are recorded with SHA-256 hashes and statement IDs in `analysis/input_provenance.json`. All figures have PNG, SVG and PDF versions. Key exports:

- `analysis/subscriber_size_bands_all_scenarios.csv`: eight known-size bands plus unknown, both registration cohorts, three source scenarios; counts, percentages, means, medians, source diversity.
- `analysis/subscriber_half_decade_bands.csv`: finer bins, denominators and rates.
- `analysis/subscriber_rank_correlations.csv`: all six channel-level cohort correlations.
- `analysis/subscriber_band_capture_recapture.csv` and `source_sensitivity_by_band.csv`: exact original five-band reconstructions for comparison.

Reproduce locally without network access:

```bash
python3 scripts/analyze_crawl9_capture_by_size.py outputs/crawl9_capture_size_2026-09-30
```

The script reads existing successful query results and validates them before publishing summary JSON and figures. Databricks tables, crawlers and estimation defaults were not modified.
