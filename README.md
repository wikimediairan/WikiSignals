# WikiSignals

**Community health and capacity analytics for Wikimedia.**

WikiSignals complements [Wikistats](https://stats.wikimedia.org) by focusing on **maintenance burden, administrative workload, governance queues, conflict signals, bot dependency, and community capacity**. Standard activity statistics are **consumed from Wikimedia Analytics (AQS)** where practical rather than reproduced.

| | |
|--|--|
| **Repository** | https://github.com/wikimediairan/WikiSignals |
| **Live example** | https://wikisignals.toolforge.org |
| **License** | [GNU GPL v3 or later](LICENSE) |
| **Default workspace** | Persian Wikipedia (`fa.wikipedia`) — **config only**, not hard-coded product logic |

## Positioning

| Product | Answers |
|---------|---------|
| **Wikistats / Wikimedia Analytics** | How much activity is happening? |
| **WikiSignals** | What operational pressures is that activity producing? |

Details: [docs/WIKISTATS_BOUNDARY.md](docs/WIKISTATS_BOUNDARY.md).

## Domains

- **Capacity** — active editors (official) as denominators  
- **Maintenance** — configured backlog tracks + backlog per active editor  
- **Governance** — process queues when configured  
- **Admin workload** — blocks, protections, deletions, moves (aggregate)  
- **Conflict** — revert rates (no user surveillance; needs wiki replicas)  
- **Automation** — bot edit share (no automatic causation claims)  
- **Official context** — edits, pageviews, etc. from AQS  

Signals are **interpretable** (improving / stable / needs attention). There is **no** opaque community health score.

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy async, Alembic |
| Database | MariaDB (ToolsDB) / SQLite for local tests |
| Frontend | Vue 3, TypeScript, ECharts, vue-i18n (English UI; FA deferred) |
| Sources | AQS, MediaWiki API, optional Toolforge wiki replicas |

## Quick start (local)

```bash
cp .env.example .env   # set a real USER_AGENT

cd backend
python3 -m venv .venv && source .venv/bin/activate
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
cd frontend && npm ci && npm run dev
```

Or: `docker compose up --build`.

Full local workflow, tests, and PR tips: **[CONTRIBUTING.md](CONTRIBUTING.md)**.

## Deploy a fresh Toolforge instance

One guide (accounts → envvars → build → migrate/seed → bootstrap → daily):

**[docs/DEPLOY.md](docs/DEPLOY.md)**

## Configuration

Add wikis and maintenance categories via `config/projects/*.yaml` —  
[docs/PROJECT_CONFIGURATION.md](docs/PROJECT_CONFIGURATION.md).

## Privacy

Aggregate systems analytics only. No volunteer or admin scoreboards.  
[docs/PRIVACY.md](docs/PRIVACY.md)

## Documentation

Index: **[docs/README.md](docs/README.md)**

| Doc | Topic |
|-----|--------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Develop and contribute |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Toolforge from zero |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/API.md](docs/API.md) | HTTP API |
| [docs/METHODOLOGY.md](docs/METHODOLOGY.md) | Metric definitions |
| [docs/SECURITY.md](docs/SECURITY.md) | Security review |
| [docs/DATA_COLLECTION.md](docs/DATA_COLLECTION.md) | Job budgets |
