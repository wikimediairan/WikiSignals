# Public API

Base path: `/api/v1`

OpenAPI interactive docs: `/docs` (when the backend is running).

All timestamps and `period_start` values are **UTC**. Aggregates are public; responses may include `Cache-Control: public`.

## Projects

### `GET /projects`

List configured Wikimedia projects.

### `GET /projects/{project_id}`

Project registry detail (`fa.wikipedia`, `tr.wikipedia`, …).

## Metrics

### `GET /metrics/definitions`

Full metric catalog with methodology fields.

### `GET /projects/{project_id}/metrics/{metric_id}`

Time series.

Query parameters:

| Param | Description |
|-------|-------------|
| `start` | `YYYY-MM-DD` (UTC) |
| `end` | `YYYY-MM-DD` (UTC) |
| `interval` | `day` \| `week` \| `month` \| `quarter` \| `year` |

Example:

```http
GET /api/v1/projects/fa.wikipedia/metrics/active-editors
```

Canonical ID form used by this service:

```http
GET /api/v1/projects/fa.wikipedia/metrics/editors.active?start=2023-01-01&end=2025-12-01&interval=month
```

### `GET /projects/{project_id}/metrics?ids=a,b,c`

Batch series for multiple metric IDs.

### `GET /projects/{project_id}/top-pages`

High-activity **pages** (not people).

- `snapshot_type=top_by_edits` | `top_by_pageviews`

### `GET /projects/{project_id}/cohorts`

New-editor funnel cohorts (requires replica-backed data).

### `GET /projects/{project_id}/annotations`

Manual event annotations.

## Compare

### `GET /compare?projects=fa.wikipedia,tr.wikipedia&metric=editors.active&start=...&end=...&interval=month`

Includes a disclaimer that raw counts are not community rankings.

## Export

### `GET /export?projects=...&metrics=...&start=...&end=...&interval=month&format=csv|json`

CSV or JSON with metric definitions/metadata alongside values.

## Methodology

### `GET /methodology`

Timezone rules, interval definitions, privacy summary, metric catalog.

## Health

### `GET /health`

Liveness, version, frontend build status, last successful ingest time.
