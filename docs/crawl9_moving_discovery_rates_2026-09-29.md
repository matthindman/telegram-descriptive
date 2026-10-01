# Crawl 9: differential discovery rates

**2026-09-29.** This follow-up compares subscriber thresholds **within crawl 9
only**. Linear axes are the default. At the user's request, the primary moving
window is narrow: **100,000 valid exposures**, approximately 1.86% of the full
5,375,849-exposure crawl. The window advances by 25,000 exposures.

![Moving discovery rates](../outputs/crawl9_rolling_2026-09-29/analysis/discovery_rates_100k_absolute.png)

## Findings

Discovery is bursty throughout the run. The primary curves preserve those local
changes instead of imposing a smooth or monotonic decline. For a common endpoint
comparison, the dashed segments show the averages over the first and last
**exactly one million** valid exposures:

| Subscribers ≥ | First 1m: new per million | Last 1m: new per million | Change |
| --- | ---: | ---: | ---: |
| 1,000 | 4,772 | 2,937 | −38.5% |
| 10,000 | 1,012 | 503 | −50.3% |
| 100,000 | 102 | 55 | −46.1% |
| 1,000,000 | 5 | 3 | −40.0% |

On this comparison, the ≥10k and ≥100k groups show larger proportional declines
than the ≥1k group. The million-subscriber group's change is five discoveries
versus three; its narrow-window curve mostly consists of zero intervals and
individual discovery bursts. These percentages describe the recorded sample;
they are not tests that the decline differs statistically between thresholds.

Five consecutive, non-overlapping, nearly equal exposure blocks give a check
beyond the two endpoint windows. Values are discoveries per million exposures:

| Exposure fifth | ≥1k | ≥10k | ≥100k | ≥1m |
| --- | ---: | ---: | ---: | ---: |
| 1 | 4,729.49 | 978.45 | 97.66 | 4.65 |
| 2 | 3,575.25 | 724.54 | 82.78 | 4.65 |
| 3 | 4,106.33 | 751.51 | 76.27 | 4.65 |
| 4 | 2,753.05 | 598.98 | 79.99 | 3.72 |
| 5 | 3,073.00 | 521.78 | 53.01 | 2.79 |

The lower ending rates are also visible across these broader blocks, with
intermediate rebounds rather than a uniform decline. Restricting the comparison
to crawl 9 removes the documented between-crawl mode changes. The mix of sources
encountered can still vary within the run; these plots do not isolate its effect
from depletion of previously unseen targets.

## Relative comparison

The companion plot divides each moving rate by that threshold's average rate in
the first million exposures. All four panels then use the same linear percentage
scale; 100% is the initial first-million rate. It uses the same 100k window.

![Relative discovery rates](../outputs/crawl9_rolling_2026-09-29/analysis/discovery_rates_100k_relative.png)

## Definitions and computation

- These are **nested thresholds**, not mutually exclusive subscriber bands.
- A discovery is a currently usable handle absent from the pre-crawl-9 seed
  frame, counted at its first valid exposure in crawl 9. Repeated encounters do
  not add discoveries. The frame cutoff is `2026-09-10 00:01:46.341 UTC`.
- All valid exposures form the denominator, including repeat encounters and
  channels below a particular threshold. The unit is one million **valid link
  exposures**, not one million distinct channels, visits, or attempted links.
- At exposure index `x`, a centered 100k window includes indices in
  `(max(0,x−50,000), min(N,x+50,000)]`. Its rate is the number of discoveries
  divided by the actual window width, multiplied by one million. The first and
  last 50k of the axis are shaded because their windows are shorter; the two
  endpoint windows each contain 50k exposures. There is an additional evaluation
  at the exact final exposure, after the last regular 25k grid point.
- Window counts come directly from first-discovery exposure indices in SQL.
  No fractional discovery counts, interpolation within existing bins, or
  assumption of uniform discovery timing was used. Lines connect the evaluated
  moving-rate points.
- Window rates are averaged over exposure effort, not elapsed clock time. The
  centered window uses observations on both sides of its plotted position.
- Size and usability use the fixed September snapshot. Usable means
  `is_channel=true`, no `invalidated_at`, and no entry in the invalid/deferred
  table. Handles, rather than fully resolved stable channel entities, are the
  available discovery identifiers. The two unexposed registry additions remain
  excluded, as in the original report.

The primary display changed from an initially planned one-million window to
100k following the user's request. A [250k sensitivity plot](../outputs/crawl9_rolling_2026-09-29/analysis/discovery_rates_250k_absolute.png)
and numerical windows of 250k, 500k, 1m, and 1.5m are retained. The displayed 100k
window was selected by the user's requested granularity, not by model fit. No
confidence bands, fitted decay constants, or population estimates were added.

## Reproducibility

The source remains `qa_catalog.telegram_link_exposure_9`, Delta versions
`link_exposure_records=28`, `seed_channels=20`, and `invalid_channels=18`.
The three SQL queries succeeded without truncated results and changed no remote
tables. Ordering matches the original crawl-9 analysis: `extracted_at`,
`sequence_id`, `visit_id`, `exposure_id`.

Validation checks cover window bounds, actual denominators, nested counts,
agreement with the original crawl-9 total discoveries, and reconciliation of
the five disjoint exposure blocks to full-crawl totals. The plotting scripts
passed Ruff and compilation; exported plots were visually inspected.

- [Primary and fixed-window SQL](../outputs/crawl9_rolling_2026-09-29/queries/01_rolling.json)
- [Narrow-window SQL](../outputs/crawl9_rolling_2026-09-29/queries/02_narrow_windows.json)
- [Results and statement provenance](../outputs/crawl9_rolling_2026-09-29/results/)
- [Plotting script](../scripts/plot_crawl9_discovery_rates.py)
- [All moving-rate data](../outputs/crawl9_rolling_2026-09-29/analysis/rolling_discovery_rates.csv)
- [First-versus-last comparison](../outputs/crawl9_rolling_2026-09-29/analysis/first_vs_last_million.csv)
- [Fixed-window counts](../outputs/crawl9_rolling_2026-09-29/analysis/fixed_window_counts.csv)
- [Primary figure PDF](../outputs/crawl9_rolling_2026-09-29/analysis/discovery_rates_100k_absolute.pdf)
- [Primary figure SVG](../outputs/crawl9_rolling_2026-09-29/analysis/discovery_rates_100k_absolute.svg)

Rebuild locally:

```bash
MPLCONFIGDIR=/private/tmp/telegram-mpl python3 scripts/plot_crawl9_discovery_rates.py outputs/crawl9_rolling_2026-09-29
```

The earlier cumulative plot script now generates linear figures by default;
`--include-log-variants` explicitly enables its optional log-y versions. Original
figures and numerical reports remain available.

## 2026-09-29 follow-up: moderate smoothing at 250k

At the user's request for slightly more smoothing, the default display now uses
a **250,000-exposure centered moving window**, approximately 4.65% of crawl 9,
still evaluated every 25,000 exposures. Both absolute-rate and relative-rate
figures use the wider window and linear axes. The prior 100k figures and their
`summary_100k.json` are retained; no data, threshold, or endpoint comparison
changed. The saved exact window counts supported this update without new
Databricks queries.

![Moving rates with 250k smoothing](../outputs/crawl9_rolling_2026-09-29/analysis/discovery_rates_250k_absolute.png)

[Relative-rate version](../outputs/crawl9_rolling_2026-09-29/analysis/discovery_rates_250k_relative.png)
uses the same smoothing. The shaded edge regions now extend 125k exposures
from either end; each endpoint rate uses its available 125k exposures.

The standard rebuild command now renders these two 250k figures. Pass
`--window 100000` to reproduce the original narrower figures. Validation
checks and Ruff passed, and both smoothed figures were visually inspected.
