# Architecture

```
Vue SPA  →  FastAPI /api/v1  →  MariaDB / ToolsDB (aggregates + provenance)
                  ▲
         Jobs write series / snapshots
                  │
   AQS (official context) · MediaWiki API (health) · wiki replicas (conflict)
```

Official analytics feed **context and denominators**. Local collectors compute **health-domain** metrics Wikistats does not provide.

## Layers

1. **Providers** — HTTP/SQL to external systems only (`providers/`)
2. **Pipeline** — normalize + upsert aggregates (`pipeline/store.py`)
3. **Services** — registry, ingest, metric read models, signals
4. **API** — versioned public read API (`/api/v1`)
5. **SPA** — shareable URL state, EN/FA, RTL/LTR (`frontend/` → `backend/app/static`)

## Multi-project design

Projects live in `config/projects/*.yaml` and the `projects` table. Metric code never branches on language or `fa.*` IDs. Persian Wikipedia is the default **workspace** via `default_for_workspace` and `DEFAULT_PROJECT_ID`.

## Jobs

| CLI | Typical use |
|-----|-------------|
| `seed-registry` | YAML → DB |
| `bootstrap` / `ingest` | Official AQS history |
| `collect-health` | Maintenance / process / admin logs (MW API) |
| `collect-replicas` | Reverts / active admins |
| `daily` | Budgeted incremental update (Toolforge schedule) |
| `diagnose` / `check-connectivity` | Ops debugging |

Failed runs can be recorded in `ingestion_runs`. Series upserts are idempotent for safe retries.

Deploy: [DEPLOY.md](DEPLOY.md) · contribute: [../CONTRIBUTING.md](../CONTRIBUTING.md).
