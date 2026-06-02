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
```

Design rule: notebooks orchestrate and inspect; shared code in `src/` implements
reusable data contracts, estimators, plots, and exports. Avoid one large
do-everything notebook.

## Start here

- `docs/telegram_descriptive_analysis_plan.md` — full sequenced plan and milestones.
- `docs/README_telegram_data_resources.md` — schema/table/variable orientation map.
- `docs/AGENT_TELEGRAM_DATA_CONTEXT.md` — context for coding agents.
- `docs/databricks_telegram_resources.agent.json` — machine-readable schema manifest.
