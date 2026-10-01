# Telegram crawl 9: initial read-only analysis

Analysis date: **2026-09-29**. Workspace identity independently verified as
`matt.hindman@researchaccelerator.org`.

## Main findings

The export really does contain **979,961 distinct exposed handles**, close to one
million, across all included crawls. That is different from the **632,088 registered
handles** and **612,589 usable registered handles**. The crawl is still discovering
channels above every configured subscriber threshold; these data do not establish
saturation or a defensible stopping point.

Crawl 9 runs from September 10 through **September 28, 2026, 15:00 UTC** in this
export. It has **73,889 source visits**, **58,930 distinct visited handles**,
**5,531,162 link-exposure rows**, **5,375,849 validated-public exposure rows**, and
**206,868 distinct targets validated as public at least once**. The export was
replaced on September 28 around 16:57–16:58 UTC. The recorded run status is
`completed`; that alone does not establish whether the daily scheduler will resume.

Chao2, a first-order incidence jackknife, and saturation models were computed as
**exploratory diagnostics**. The empirical counts/curves are usable now. The
population estimates are not validated: chain effort is very unequal, 170 recorded
chain IDs have no valid exposure, burn-in is unverified, and fixed-lookback settings
are absent from the exported tables.

## Reconcile the channel totals

| Measure | Count | Meaning |
| --- | --- | --- |
| All known handles | 1,398,630 | Union of registry, discovery, invalid, and exposure records |
| Exposed handles, all runs | 979,961 | Includes failed/non-channel validation targets |
| Registered seed handles | 632,088 | The seed table grows during crawling |
| Discovered-table handles | 470,806 | All are already present in the seed table |
| Seed/discovered union | 632,088 | Do not add the two tables |
| Usable registered handles | 612,589 | Seed not invalidated and absent from invalid/deferred table |
| After merging known chat-ID aliases | 611,126 | Remaining unknown IDs prevent complete identity deduplication |
| Invalid/deferred-table handles | 786,041 | Mostly not_supergroup, not_found, non_channel, and no_count |
| Distinct validated targets, crawl 9 | 206,868 | Validation-at-exposure population, before current-status exclusions |

The 612,589 usable records are all marked `is_channel=true`. Four lack subscriber
counts. There are 536,618 usable handles without a nonzero chat ID. Among those
with IDs, 1,040 IDs map to multiple handles, contributing 1,463 extra handle rows.
Thus none of the handle totals should be described as a fully deduplicated count
of Telegram entities. The earlier chat figure of 608,381 usable channels was a
September 27 report; this is a newer, directly queried snapshot.

## Subscriber thresholds and discoveries

The primary descriptive analysis follows the crawler's handle identifiers.
Usable means `is_channel=true`, `invalidated_at IS NULL`, and no matching entry in
`invalid_channels`, including the three deferred giant channels. Size is taken
from `seed_channels.member_count` in the fixed export. It is **not an exposure-time
measurement** and its measurement date is not stored. Historical eligibility and
size changes cannot be reconstructed from these tables.

| Subscribers ≥ | Usable handles | Added during crawl 9 | Known-ID deduplicated entries | New known-ID entries |
| --- | --- | --- | --- | --- |
| 1,000 | 170,512 | 19,610 | 170,162 | 19,514 |
| 10,000 | 47,244 | 3,844 | 47,031 | 3,790 |
| 100,000 | 6,903 | 419 | 6,845 | 408 |
| 1,000,000 | 456 | 22 | 451 | 22 |

The known-ID sensitivity merges aliases using nonzero chat ID, falls back to
handle where absent, takes maximum member count across aliases, and treats an
entity as pre-existing if any alias predates crawl start. The maximum-count rule
is a labeled sensitivity, not a change to the project's metric-snapshot default.
There are 304 multi-handle entities with conflicting registry subscriber counts.

The registry membership at crawl start can be reconstructed consistently:
524,542 raw seed rows predate `2026-09-10 00:01:46.341 UTC`, while 107,546 were
inserted afterward and tagged with crawl 9; there are no contradictory tags or
missing insertion timestamps. Of the new rows, 107,306 remain usable in this
snapshot. Because this is retrospective current-usability filtering, these counts
can differ from operational reports made on earlier dates.

Two new usable seed handles (subscriber counts 9,440 and 6,160) never appear as
valid crawl-9 exposures. Therefore the exposure-based curve has 19,608 new ≥1k
handles versus the registry's 19,610. The ≥10k, ≥100k, and ≥1m counts agree exactly.

![Subscriber discovery curves](../outputs/crawl9_2026-09-29/analysis/subscriber_discovery_curves.png)

The last **975,849 valid exposures** (from exposure 4.4 million onward) added:

| Subscribers ≥ | First 1m exposures: new | Last 975,849: new | Last-window new per 100k exposures |
| --- | --- | --- | --- |
| 1,000 | 4,772 | 2,869 | 294.00 |
| 10,000 | 1,012 | 491 | 50.32 |
| 100,000 | 102 | 55 | 5.64 |
| 1,000,000 | 5 | 3 | 0.31 |

Discovery yield is lower than at the start, but remains positive at every
threshold. The million-subscriber group is sparse—only 22 new handles—so its
apparently flatter curve should not be interpreted as demonstrated closure.
The latest UTC day added 4,335 currently usable handles, including 772 ≥1k,
134 ≥10k, 23 ≥100k, and one ≥1m. Counts are classified using the current export.

![Discovery yield](../outputs/crawl9_2026-09-29/analysis/subscriber_discovery_yield.png)

## Chao2 and comparable incidence diagnostics

The existing core `chao2_from_counts` implementation was run on actual crawl-9
sufficient statistics, using its unchanged bias-corrected formula:

`S_obs + ((m-1)/m) * Q1*(Q1-1) / (2*(Q2+1))`.

Here `m=1,814` recorded chain IDs. For each threshold, pre-crawl members are removed
from the incidence calculation and added back as an offset. Q1/Q2 count targets
seen in exactly one/two recorded chain IDs, not the number of followed links or
raw repeated mentions. All validated exposures count toward sampling effort,
including those below a subscriber threshold.

**These are mechanical diagnostic values, not defensible lower bounds or
confidence intervals for the current population.** No burn-in was selected and
recorded chain IDs have not been verified as independent sampling units.

| Subscribers ≥ | Pre-crawl offset | Observed new | Q1 | Q2 | Chao2 + offset | Jackknife 1 + offset |
| --- | --- | --- | --- | --- | --- | --- |
| 1,000 | 150,902 | 19,608 | 11,210 | 3,568 | 188,104 | 181,714 |
| 10,000 | 43,400 | 3,844 | 2,188 | 734 | 50,497 | 49,431 |
| 100,000 | 6,484 | 419 | 254 | 92 | 7,248 | 7,157 |
| 1,000,000 | 434 | 22 | 10 | 6 | 462 | 466 |

The first-order jackknife uses `S_obs + Q1*(m-1)/m`, plus the same offset; see the
[vegan authors' incidence-estimator documentation](https://github.com/vegandevs/vegan/blob/master/vignettes/diversity-vegan.Rnw).
No classical-Chao switch replaced the project's registered bias-corrected formula.
These figures do not justify reporting percent complete or a total for all Telegram.

The prescribed all-chain equal-effort analysis cannot currently run: minimum
eligible exposure effort is **zero**. There are 1,644 positive-effort chain IDs,
with 1,440 reaching 25 exposures, 1,152 reaching 100, 367 reaching 1,000, and 147
reaching 10,000. The report preserves all these retention/truncation sensitivities
in `chain_effort_sensitivity.csv`; they condition on different subsets and are
not comparable full-population lower bounds. Only 25 chain IDs begin at depth
zero, while most start at positive depths. That is a reason to verify chain-ID
semantics, not proof that exactly 25 independent chains can be reconstructed.

## Saturation model checks

Simple and stretched exponentials were fitted to discovery **increments** in
100,000-valid-exposure bins. The last bin uses its actual size. The first 43 bins
were used for fitting and the last 11 for an initial chronological holdout;
Poisson deviance is used as a predictive score, without assuming independent
observations for inferential intervals. A constant discovery-rate baseline was
also scored. This is an initial holdout diagnostic, not completed multi-window
validation or an approved stopping rule.

| Subscribers ≥ | Lowest holdout deviance | Held-out new observed | Simple-model prediction | Full simple asymptote + offset |
| --- | --- | --- | --- | --- |
| 1,000 | simple_exponential | 3,304 | 2775.4 | 191,732 |
| 10,000 | simple_exponential | 561 | 542.2 | 50,209 |
| 100,000 | simple_exponential | 57 | 68.9 | 7,305 |
| 1,000,000 | simple_exponential | 3 | 3.1 | 471 |

The simple exponential scores best among the tested models at the four configured
subscriber thresholds. However, every full-data stretched-exponential fit hits
the upper timescale search boundary, so its finite asymptote is unidentified over
the observed range. At the descriptive all-size threshold, stretched exponential
scores best in holdout despite that unresolved asymptote. Thus reasonable
curve families do not establish a stable final population size. No selected
population estimate, monotone survival estimate, or Chao-constrained confidence
interval is asserted. All model scores and boundary flags are retained.

The repository's original `fit_simple_saturation` helper was also executed and
saved as a replay, but it fits cumulative residuals and was not used for the
increment-based model comparison. Existing defaults were unchanged.

## Hub concentration and data-quality findings

`fragment_monitor` contributes 2,348,372 / 5,375,849 = **43.68%** of valid crawl-9
exposures, from only 61 visits and 58 recorded chain IDs. `lelang_username` adds
90,846 exposures from two visits. These are source-visit observations; duplicate
mentions within a visit have already been collapsed.

Removing `fragment_monitor` alone loses 6,360 currently usable observed targets,
including 121 ≥10k, 25 ≥100k, and two ≥1m. Removing both hubs loses 49,757 targets,
including 705 ≥10k, 124 ≥100k, and ten ≥1m. The main results retain all sources;
removal changes the observed population and is only a sensitivity analysis.
`hub_sensitivity.csv` also records how their removal changes the Q1/Q2-based
calculations.

Measured integrity checks:

- All crawl-9 visits and exposures record `candidate_mode=all_valid`.
- Zero duplicate `(batch_id,target_channel)` exposure keys; zero duplicate visit IDs.
- Zero orphan exposures, chain mismatches, or source mismatches at the visit join.
- Exposure ordering fields are complete.
- All 5,531,162 exposure-time subscriber fields are NULL. Registry joins recover
  nearly all counts; the main four subscriber thresholds use known registry values.
- `target_is_pre_crawl_seed` is false for 1,067 valid exposure rows covering 129
  handles that demonstrably predate crawl start. The analysis reconstructs membership
  from insertion time instead of trusting that flag.
- All 42,476 exposure-backed source visits lack scan start/end timestamps.
  Their exposure timestamps provide event-time proxies. The other 31,413 visits
  have scan timestamps, no batch ID, and forced-walkback outcomes. No forced-walkback
  visits were dropped when counting effort or recorded chain IDs.
- The export contains no fixed-lookback flag/window or frozen configuration payload.
  The chat logs describe 60 days, but the data cannot verify deployment or anchoring.
- Four usable registry handles lack subscriber counts; subscriber measurement
  timestamps and complete stable channel identities remain unavailable.

## What needs resolution before a publication-grade estimate

1. Confirm the meaning and lifecycle of `chain_id` and how independent walkers,
   restarts, and walkbacks map into it; obtain a persistent walker/root identifier
   if needed. Do not silently drop zero-effort units to make estimates run.
2. Retrieve the actual crawl-9 lookback/configuration record and establish burn-in
   using the prescribed convergence diagnostics. Keep current curves descriptive.
3. Repair exposure-time subscriber recording, complete visit timestamps, and
   confirm the pre-crawl seed-flag semantics. Retain explicit unknown metric cases.
4. Resolve known aliases and document the population's eligibility/size snapshot.
5. Re-run the registered equal-effort estimator and whole-chain uncertainty, with
   hub sensitivity and repeated later-window predictive checks. Report remaining
   disagreement or failure to identify an asymptote.

## Reproducibility and verification

All **42 Databricks statements** in this audit were SELECT/WITH,
SHOW, or DESCRIBE reads on the existing warehouse `86100da4e1fe8713`. No Databricks
tables, crawler settings, permissions, or schedules were changed. Local output
artifacts contain aggregate results and non-content identifier diagnostics.
Each result JSON records SQL, statement ID, schema, row counts, and query times.

Fixed Delta versions:

| Table | Version |
| --- | --- |
| crawl_runs | 18 |
| discovered_channels | 18 |
| edge_records | 20 |
| invalid_channels | 18 |
| link_exposure_records | 28 |
| seed_channels | 20 |
| source_visit_records | 18 |

Sources are `qa_catalog.telegram_link_exposure_9.<table>`. The schema contains
historical runs too, so crawl-9 exposure/visit analyses explicitly filter
`crawl_id='telegram-link-exposure-9'`. Registry/frame totals intentionally include
historical seed membership. Schema 9 was the newest Telegram crawl schema listed.

- Code at start: `869f6d0`, matching GitHub main at the preceding status check.
- Core local test suite: **48 passed**.
- New increment-fitting numerical checks: synthetic simple/stretched parameter
  recovery, constant-rate predictions, and zero-discovery behavior all passed.
- Aggregate checks reconcile daily visits/exposures and curve totals exactly.
- Ruff and Python compilation checks passed for the two new analysis scripts.
- Figures were rendered and visually inspected.

Local artifacts: `outputs/crawl9_2026-09-29/queries/`, `results/`, and `analysis/`.
Run local numerical analysis again with:

```bash
PYTHONPATH=src python3 scripts/analyze_crawl9_readonly.py outputs/crawl9_2026-09-29
```

The query runner is `scripts/databricks_readonly_audit.py`; it uses the existing
OAuth profile, reads a saved query batch, checks completion/truncation, and writes
results locally. Remote queries require the Databricks SDK and network access;
local numerical analysis requires NumPy, pandas, Matplotlib, and SciPy.

## 2026-09-29 follow-up: crawls 3–9

The requested extension now plots cumulative subscriber discovery across crawls
3–9, with repeated discoveries counted once and a baseline reconstructed before
crawl 3. See [the follow-up report](saturation_crawls3_to9_2026-09-29.md) for the
figures, per-crawl contributions, and reproducible query results. The original
crawl-9 diagnostics above are retained unchanged.

## 2026-09-29 clarification: flattening versus completeness

The earlier sentence about the million-subscriber group was too easy to read as
dismissing evidence of flattening. The low discovery rate is evidence of
diminishing returns; the fact that only 22 new handles were found does not negate
that evidence. Those additions increased the known inventory from 434 to 456
(5.1%) over 5,375,849 valid exposures, or 4.09 new handles per million exposures.
Crawl 4 yielded 282.57 per million and crawl 6 yielded 100.05; the later phase
is much flatter, although differences in the crawl process limit attribution.

There is a narrower unresolved question: whether this low rate is continuing to
decline toward zero, and how many handles remain unobserved. Crawls 7, 8, and 9
yielded 1.68, 3.70, and 4.09 newly found million-subscriber handles per million
valid exposures, respectively. Within crawl 9, the first million exposures added
five handles and the final 975,849 added three. These sparse, dependent events
do not establish a sustained within-run decline, even though the combined curve
has clearly flattened relative to the early phase.

The intended interpretation is: **discovery has slowed markedly, consistent with
approaching saturation under this crawl; the remaining population and fraction
covered have not yet been established.** Continued discoveries do not by
themselves refute approaching saturation. Conversely, low discovery yield alone
does not determine the number of very difficult-to-detect channels. This latter
distinction is discussed in [Chao et al. (2014), p. 54](https://www.robertkcolwell.org/publications/6842.pdf):
unseen richness and the probability mass of unobserved species are different
quantities. Subscriber size is not a known channel-detection probability here.

This is an interpretive clarification, not a change to any numerical results or
estimator defaults. Rates were checked against the saved crawl endpoints and
the original 100,000-exposure-bin query results; no new Databricks queries ran.

## 2026-09-29 follow-up: narrow moving discovery rates

The [within-crawl-9 rate analysis](crawl9_moving_discovery_rates_2026-09-29.md)
now shows centered 100,000-exposure moving rates at the four subscriber
thresholds, on linear axes. Exact first-versus-last-million windows and five
disjoint exposure blocks accompany the narrow curves. This comparison avoids
pooling the differently configured earlier crawls.

## 2026-09-30 follow-up: subscribers and capture/recapture

The [subscriber-size analysis](crawl9_capture_by_subscribers_2026-09-30.md)
now measures capture of the retained pre-crawl inventory, conditional recapture
in distinct recorded chain IDs, and channel-level rank correlations. It separates
previously known and newly registered handles and checks sensitivity to the two
major link-list sources. The new direct queries exactly reproduce this audit's
original threshold totals on the same Delta versions. Subscriber size has a
positive association with recurrence among previously known captured handles
above 1,000 subscribers, but essentially no rank association among new captures
over that range. Extremely recurrent small handles make pooled correlations
misleading. The original numerical results and estimator defaults remain unchanged.
