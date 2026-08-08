# WikiSignals

**Community health and capacity analytics for Wikimedia.**

WikiSignals complements [Wikistats](https://stats.wikimedia.org) by analyzing **maintenance burden, administrative workload, governance queues, conflict signals, bot dependency, and community capacity**. Standard activity statistics are **consumed from Wikimedia’s official analytics infrastructure** where practical rather than unnecessarily reproduced.

**Repository:** https://github.com/wikimediairan/WikiSignals  

**Default workspace:** Persian Wikipedia (`fa.wikipedia`) — configuration, not hard-coded product logic.

## Positioning

| Product | Answers |
|---------|---------|
| **Wikistats / Wikimedia Analytics** | How much activity is happening? |
| **WikiSignals** | What operational pressures is that activity producing? |

See [docs/WIKISTATS_BOUNDARY.md](docs/WIKISTATS_BOUNDARY.md).

## Primary domains

- **Capacity** — active editors (official) as denominators  
- **Maintenance** — configured backlog tracks + backlog per active editor  
- **Governance** — process queues when configured  
- **Admin workload** — blocks, protections, deletions, moves (aggregate)  
- **Conflict signals** — revert rates (no user surveillance)  
- **Automation** — bot edit share (no automatic causation claims)  
- **Official context** — edits, pageviews, etc. from AQS  

Signals are **interpretable** (improving / stable / needs attention). There is **no** opaque community health score.

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy async, Alembic |
| Database | MariaDB (ToolsDB) / SQLite for tests |
| Frontend | Vue 3, TypeScript, ECharts, vue-i18n (EN + FA, RTL) |
| Sources | Wikimedia AQS (context), MediaWiki API (health collectors), optional replicas |

**License:** [GNU GPL v3 or later](LICENSE)

## Quick start

```bash
cp .env.example .env   # set USER_AGENT

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=sqlite+aiosqlite:///./wikisignals.db
export USER_AGENT='WikiSignals/0.1 (https://github.com/wikimediairan/WikiSignals; you@example.org)'
export PYTHONPATH=.
alembic upgrade head
python -m app.jobs.cli bootstrap --project fa.wikipedia --months 12
python -m app.jobs.cli collect-health --project fa.wikipedia --months 1
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

Docker: `docker compose up --build`

## CLI

```bash
python -m app.jobs.cli bootstrap --project fa.wikipedia
python -m app.jobs.cli ingest --project fa.wikipedia
python -m app.jobs.cli collect-health --project fa.wikipedia
python -m app.jobs.cli daily --project fa.wikipedia
python -m app.jobs.cli compute-signals --project fa.wikipedia
python -m app.jobs.cli check-connectivity
python -m app.jobs.cli verify --project fa.wikipedia --metric editors.active --month 2026-01
```

## Toolforge

**Step-by-step deploy:** [docs/TOOLFORGE_STEP_BY_STEP.md](docs/TOOLFORGE_STEP_BY_STEP.md)  
Reference + budgets: [docs/toolforge.md](docs/toolforge.md) · [docs/DATA_COLLECTION.md](docs/DATA_COLLECTION.md)  
Security: [docs/SECURITY.md](docs/SECURITY.md)

## API examples

```http
GET /api/v1/projects/fa.wikipedia/health
GET /api/v1/projects/fa.wikipedia/backlogs
GET /api/v1/projects/fa.wikipedia/metrics/maintenance.backlog_per_active_editor?interval=month
GET /api/v1/methodology
```

## Configuration

Add wikis and maintenance categories via `config/projects/*.yaml` — see [docs/PROJECT_CONFIGURATION.md](docs/PROJECT_CONFIGURATION.md).

## Privacy

Aggregate systems analytics only. No volunteer or admin scoreboards. [docs/PRIVACY.md](docs/PRIVACY.md)

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Methodology](docs/METHODOLOGY.md)
- [API](docs/API.md)
- [Wikistats boundary](docs/WIKISTATS_BOUNDARY.md)
- [Contributing](CONTRIBUTING.md)
