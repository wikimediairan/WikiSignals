# Architecture

```
Vue SPA (health-first)  →  FastAPI /api/v1  →  MariaDB aggregates + provenance
                                ↑
              Jobs: AQS context · collect-health · compute-signals
                                ↑
     Official AQS (context) │ MW collectors (backlog, logs, processes) │ Replicas (opt.)
```

Official analytics feed **context and denominators**. Local collectors compute **health-domain** metrics Wikistats does not provide.

## Layers

1. **Providers** — HTTP/SQL to external systems only
2. **Pipeline** — normalize + upsert aggregates
3. **Services** — registry, ingest, metric read models
4. **API** — versioned public read API
5. **SPA** — shareable URL state, EN/FA, RTL/LTR

## Multi-project design

Projects live in `config/projects/*.yaml` and the `projects` table. Metric code never branches on language or `fa.*` IDs. Persian Wikipedia is the default **workspace** via `default_for_workspace` and `DEFAULT_PROJECT_ID`.

## Jobs

```bash
python -m app.jobs.cli bootstrap
python -m app.jobs.cli ingest --project fa.wikipedia
python -m app.jobs.cli ingest --all
python -m app.jobs.cli verify --project fa.wikipedia --metric editors.active --month 2024-06
```

Failed runs are recorded in `ingestion_runs`. Upserts are idempotent for safe retries.
