# Random-Walk Crawl Methods

The random-walk crawl line supports channel-count discovery completeness. It is
not a denominator for total audience mass by itself.

## Required Lineage

Population estimation requires:

- Walk events: run ID, chain ID, step ID, timestamp, candidate targets, followed
  target, decision type, restart/walkback flags, and validator status.
- Validation events: candidate URL/handle, normalized username, validation
  timestamp, public/broadcast/supergroup status, follower count, and failure
  reason.
- Exposures: duplicate-collapsed eligible target exposure rows with run, chain,
  exposure ID, target channel, eligibility, timestamp, and follower count.
- Seed/run metadata: seed source, draw probability where applicable, source
  list, and crawl run version.

## Current Status

The probed `prod_tads.telegram_random_walk` bronze table exposes `depth`,
`error`, `id`, `messages`, `parentId`, `status`, and `timestamp`. These fields
may help reconstruct parentage, but they are not enough to support rigorous
walk-event, validation, or exposure accounting without semantic confirmation.

## Implemented Behavior

Notebook 01 emits a structured gap report by default. Notebook 02 refuses to
manufacture population estimates when lineage is absent.

## Diagnostics When Inputs Exist

- Step mix over crawl time.
- Chain-level depth, step count, unique sources, and unique targets.
- Restart/walkback/forced-walkback rates.
- Candidate extraction and validation funnel.
- Duplicate URL/handle exposure rates.
- Chain-equalized post-burn-in incidence tables.
- Chao2 lower bounds with chains as replicated samples.
- Saturation curves and monotone threshold survival estimates.

