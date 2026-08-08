# Methodology

All internal timestamps and period boundaries use **UTC**.

## Product principle

Wikistats / Wikimedia Analytics measure **activity volume**.  
WikiSignals measures **operational and community pressures**.

**Rule:** Do not independently reproduce a metric already authoritatively provided by Wikimedia Analytics or Wikistats unless there is a specific technical reason. Prefer consuming official metrics with provenance. Spend local computation on metrics Wikistats does not provide.

See [WIKISTATS_BOUNDARY.md](WIKISTATS_BOUNDARY.md).

## Signals (not a score)

Health UI surfaces interpretable signals with transparent MoM rules (`improving` / `stable` / `needs_attention`). There is **no** single community health score and no whole-community “unhealthy” label.

## Intervals

| Interval | Boundary |
|----------|----------|
| day | Calendar day `[00:00, 24:00)` UTC |
| week | ISO week starting **Monday** 00:00 UTC |
| month | First day of calendar month 00:00 UTC |
| quarter | Jan/Apr/Jul/Oct 00:00 UTC |
| year | 1 January 00:00 UTC |

## Primary source: Wikimedia Analytics API (AQS)

Base URL: `https://wikimedia.org/api/rest_v1/metrics/`

AQS-backed metrics store the values returned by the API (or simple sums of AQS series). They are **not** re-derived from dumps unless documented.

### Active editors (`editors.active`)

**Definition:** Registered non-bot editors with **≥5 edits** in the period (aligned with [Research:Active editor](https://meta.wikimedia.org/wiki/Research:Active_editor) / Wikistats activity threshold).

**Calculation:** Sum of AQS `editors/aggregate` for `editor-type=user` activity levels:

- `5..24-edits`
- `25..99-edits`
- `100..-edits`

**Caveats:** Includes redirect pages per AQS. Dump-based Research definitions may differ (content namespaces, archive tables).

### Highly active editors (`editors.highly_active`)

AQS `100..-edits` for `editor-type=user`.

### Edits by editor type

AQS `edits/aggregate` for:

- `all-editor-types` → `edits.total`
- `user` → `edits.user`
- `group-bot` → `edits.group_bot`
- `name-bot` → `edits.name_bot`
- `anonymous` → `edits.anonymous`

### New registered users

AQS `registered-users/new` → `editors.new_accounts`.

Registration ≠ first edit.

### New / edited pages

AQS `edited-pages/new` and `edited-pages/aggregate`. Content-only variants use `page-type=content`.

**Do not** treat raw article counts as quality.

### Pageviews & unique devices

- Pageviews: `pageviews/aggregate` with `agent=user` (excludes spiders)
- Unique devices: `unique-devices`

Pageview data typically lags ~24–48 hours.

## Secondary source: MediaWiki Action API

Experimental aggregates for delete and block log events. Best-effort pagination; large wikis may truncate. Status: `experimental`.

## Optional source: Toolforge wiki replicas

Required for production-quality:

- New editor funnel / retention cohorts
- Returning editors
- Revert rates (`mw-reverted` tags) and newcomer revert rates

When replicas are unavailable, the API returns status `unavailable` with an explicit reason. The UI does **not** invent numbers.

## Comparison

Cross-project charts share a metric definition. Raw counts are **not** rankings of community quality.

## Annotations

Manually supplied community events only. The system never infers causality.

## Metric catalog

Canonical definitions ship in `config/metrics/catalog.yaml` and are exposed at:

- `GET /api/v1/methodology`
- `GET /api/v1/metrics/definitions`

Every displayed metric includes: ID, display name, definition, methodology, source, caveats, privacy notes, status.
