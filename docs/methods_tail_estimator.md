# Rank-Tail Denominator Estimator

The rank-tail estimator is implemented in
`telegram_descriptive.estimation.rank_tail`.

## Estimand

The estimator targets unobserved member/view mass below a trusted observed head,
separately from random-walk discovery completeness. Candidate metrics are:

- `follower_count` as the member/subscriber metric, pending semantic
  confirmation.
- `views_count` as a channel-level view metric.
- Approved post-view aggregates from `post_view_count`.

## Boundary

Candidate trusted-head boundaries `r_c` should be chosen using:

- Crawl closure evidence where available.
- Overlap with source lists and observed TOO coverage.
- Recent high-rank discovery diagnostics.
- Stability across a boundary grid.

## Local Parameter Fit

The implemented local fit uses a tricube-weighted quadratic regression of
`log(metric)` on centered `log(rank)` around `r_c`.

Definitions:

- `y0`: smoothed metric value at `r_c`.
- `alpha0 = -d log(y) / d log(rank)`.
- `eta0 = d alpha / d log(rank)`, constrained nonnegative when fitting the
  D1-D3 ladder.
- `eta1 = d eta0 / d log(rank)` and `eta2 = d eta1 / d log(rank)`, estimated
  from staggered local quadratic fits around `r_c` and constrained nonnegative.
  If the staggered estimate cannot recover a positive high-order term but a
  local quartic fit does, the implementation uses the quartic value and emits a
  fallback diagnostic flag.

## Model Ladder

- D0: constant `alpha`, pure power-law tail.
- D1: nonnegative local steepening via `eta0`.
- D2: accelerating steepening via `eta1`.
- D3: one additional nonnegative derivative via `eta2`.

The current implementation integrates the continuous tail after `r_c`. D0
requires `alpha0 > 1` for an infinite-support finite tail. D1-D3 use numerical
integration with nonnegative shape terms, so they should not exceed D0 when
shape constraints are satisfied. If the active model has no positive shape term
and `alpha0 <= 1`, it returns an infinite tail with an explicit diagnostic flag
instead of a finite artifact from an arbitrary integration cutoff.

## Diagnostics

Report:

- Boundary rank and fitting-window size.
- `alpha0 <= 1` flags.
- Convexity/curvature flags.
- D0-D3 ordering.
- Degenerate model flags when D1, D2, or D3 collapses to the previous model
  because the relevant shape term was zero or constrained to zero.
- Boundary sensitivity.
- Applicability failure when a trusted observed head is not available.
