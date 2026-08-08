# Refactor report — Community Health Observatory

## Architecture discovered (pre-refactor)

Modular FastAPI + Vue SPA monorepo with:

- AQS-first ingestion of activity metrics
- Project YAML registry (default `fa.wikipedia`)
- Metric catalog + methodology API
- Annotations, compare, export
- Soft stubs for reverts/cohorts (replicas)

## Features retained

- AQS official metrics pipeline (now **official_context** role)
- Project selector, timelines, compare, export, EN/FA RTL, Docker/Toolforge docs
- Existing API series endpoints (compat)
- Job framework (`bootstrap`, `ingest`, `verify`)

## Duplicated Wikistats features removed/deemphasized

| Existing feature | Decision | Reason |
|------------------|----------|--------|
| Overview as activity dashboard | Replaced by Health signal board | Overlapped Wikistats |
| Editors activity histograms | Deprecated role; UI redirected to Context | Official activity detail |
| Content / pageviews primary pages | Moved to Official context | Wikistats domain |
| New editor funnel primary UX | Soft-deprecated API + UI callout | New Editor Health Dashboard product boundary |
| Raw “activity observatory” branding | Renamed Community Health Observatory | Positioning |

## New community-health modules

- Maintenance backlog tracks (config-driven category snapshots)
- Administrative log workload (block/protect/delete/move/rights)
- Process/governance tracks (config)
- Derived signals: backlog/editor, admin actions/editor, bot edit share
- Health API + transparent MoM status rules
- Health-first SPA domains

## Schema changes

Migration `002_community_health`:

- Extended `metric_definitions` (domain, role, formula, provenance, deprecation)
- Extended `metric_points` (metric_version, config_version, source_retrieved_at)
- `projects.health_config`
- `annotations.category`, `visibility`
- `backlog_snapshots`, `process_snapshots`

Existing data preserved via additive migration.

## Migration process

```bash
alembic upgrade head
python -m app.jobs.cli seed-registry
python -m app.jobs.cli collect-health --project fa.wikipedia --months 1
```

## External Wikistats / Analytics integration

AQS remains the official adapter for editors, edits, pageviews. Provenance notes and `role=official_context` mark these series. UI “Official context” and signal denominators consume them.

## Persian Wikipedia configuration

Ships strong **structure** with placeholder maintenance/process tracks (`enabled: false`, `category: null`) until locally verified. Admin log collection validated live against fa.wikipedia.

## Validation performed

| Check | Status |
|-------|--------|
| Alembic 001→002 on existing SQLite | OK |
| Unit/integration tests | **29 passed** |
| `collect-health` admin logs for fa.wikipedia | OK (blocks, protect, delete, move, rights) |
| Official AQS context still in DB from prior bootstrap | OK |
| Frontend production build | OK |
| Live AQS verify | May 403 under rate limit; prior exact match still valid for stored series |

## Automated test results

```
29 passed
```

## Performance considerations

- Admin log collection is paginated and capped (`max_pages`); large wikis may truncate (experimental).
- No heavy work on request path; signals read precomputed aggregates.
- Prefer Toolforge replicas for reverts and unique active admins later.

## Remaining limitations

- Maintenance categories for fa.wikipedia not auto-filled (avoid inventing titles)
- Revert rate still needs replica/tag pipeline for stable monthly counts
- Unique active administrators not computed without replicas
- Entered/left backlog membership deltas not available from categoryinfo alone
- Deletion discussion duration percentiles deferred

## Recommended next improvements

1. Community verification of fa.wikipedia maintenance/process category titles
2. Toolforge replica SQL for reverts + active admins
3. Historical backlog time series via scheduled daily snapshots
4. Wire New Editor Health Dashboard URL when that service exists
5. Optional write API for annotations with auth

---

### Table 1 — Existing features

| Existing feature | Decision | Reason |
|------------------|----------|--------|
| edits.* (AQS) | Contextualized | Official analytics; denominators/context |
| editors.active / highly_active | Contextualized | Capacity denominators |
| editors.activity_* | Deprecated (API kept) | Wikistats-like distribution |
| pageviews / unique devices | Contextualized | Pure Wikistats |
| content.pages_* (AQS) | Contextualized | Activity volume |
| content.pages_deleted | Expanded → admin.deletions | Health domain |
| moderation.blocks | Expanded → admin.blocks | Health domain |
| reverts.* | Retained as health | Unique conflict signal |
| funnel.* | Deprecated primary UX | Product boundary |
| Compare / export / i18n | Retained | Infrastructure |
| Annotations | Retained + category/visibility | Local events |

### Table 2 — New health signals

| New health signal | Source | Method | Validation status |
|-------------------|--------|--------|-------------------|
| admin.blocks / unblocks | MediaWiki logevents | Aggregate by month | Live fa.wikipedia collection OK |
| admin.protections / unprotections | MediaWiki logevents | Aggregate by month | Live OK |
| admin.deletions / undeletions | MediaWiki logevents | Aggregate by month | Live OK |
| admin.moves / rights_changes | MediaWiki logevents | Aggregate by month | Live OK |
| admin.actions_total | Derived | Sum of admin families | Computed from collected logs |
| admin.actions_per_active_editor | Derived | actions / editors.active | Computed when both present |
| maintenance.open_total | MW categoryinfo | Sum enabled tracks | Structure OK; tracks disabled until configured |
| maintenance.backlog_per_active_editor | Derived | open_total / editors.active | Ready when tracks enabled |
| automation.bot_edit_share | Derived from AQS | (group_bot+name_bot)/total | Computed from stored AQS |
| Health MoM status rules | Config thresholds | Transparent classify | Unit tested |
