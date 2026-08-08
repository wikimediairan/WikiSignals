# Contributing to WikiSignals

Thank you for helping improve **WikiSignals** — community health and capacity analytics for Wikimedia.

**Source:** https://github.com/wikimediairan/WikiSignals  
**License:** contributions are accepted under **GNU GPL v3 or later**.

---

## What to work on

Good fits:

- Project YAML / maintenance tracks for a wiki you know  
- Metric catalog definitions and methodology text  
- Collectors, API, or SPA bugs and polish  
- Docs that stay accurate for a **fresh** deploy  
- Tests and load-safety around AQS / MediaWiki / replicas  

Out of scope without discussion:

- Individual volunteer scoreboards or surveillance UX  
- Replacing Wikistats as a general activity dashboard  
- Unbounded scrapes of revision history or user lists  

Product boundary: [docs/WIKISTATS_BOUNDARY.md](docs/WIKISTATS_BOUNDARY.md) · privacy: [docs/PRIVACY.md](docs/PRIVACY.md).

---

## Development setup

### Requirements

- Python **3.12+**
- Node.js **20+** (frontend)
- Optional: Docker + Compose for MariaDB

### 1. Clone and env

```bash
git clone https://github.com/wikimediairan/WikiSignals.git
cd WikiSignals
cp .env.example .env
# Edit USER_AGENT: real contact URL or email (required for Wikimedia APIs)
```

### 2. Option A — Docker Compose

```bash
docker compose up --build
# API:  http://localhost:8000
# SPA:  http://localhost:5173 (if frontend service is defined) or build into static
```

Compose uses `backend/Dockerfile` and mounts `config/` for local work. Toolforge does **not** use that Dockerfile.

### 3. Option B — local venv + SQLite

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

export DATABASE_URL=sqlite+aiosqlite:///./wikisignals.db
export USER_AGENT='WikiSignals/0.1 (https://github.com/wikimediairan/WikiSignals; you@example.org)'
export PYTHONPATH=.

alembic upgrade head
python -m app.jobs.cli bootstrap --project fa.wikipedia --months 12
python -m app.jobs.cli collect-health --project fa.wikipedia --months 1
# Optional reverts (needs wiki replicas — usually Toolforge only):
# python -m app.jobs.cli collect-replicas --project fa.wikipedia --months 6

uvicorn app.main:app --reload --port 8000
```

Frontend (separate terminal):

```bash
cd frontend
npm ci
npm run dev
# http://localhost:5173 → proxies /api to backend if configured, or set CORS
```

Production-style static UI (what Toolforge serves):

```bash
cd frontend && npm ci && npm run build
# writes into backend/app/static
```

---

## CLI reference

Run from `backend/` with `PYTHONPATH=.`:

| Command | Purpose |
|---------|---------|
| `seed-registry` | Load projects/metrics/annotations from YAML |
| `bootstrap` | Seed + AQS history |
| `ingest` | AQS only |
| `collect-health` | Maintenance, processes, admin logs (MW API) |
| `collect-replicas` | Reverts / active admins (wiki replicas) |
| `daily` | Budgeted incremental update |
| `compute-signals` | Derived ratios + signal summary |
| `diagnose` | Config/DB/replicas readiness (no secrets) |
| `check-connectivity` | Live AQS + MediaWiki UA probe |
| `verify` | Spot-check a stored metric point |

Examples:

```bash
python -m app.jobs.cli diagnose
python -m app.jobs.cli daily --project fa.wikipedia
python -m app.jobs.cli verify --project fa.wikipedia --metric editors.active --month 2026-01
```

---

## Tests

```bash
cd backend
source .venv/bin/activate
export PYTHONPATH=.
pytest -q                 # unit + integration (no live network)
pytest -m smoke           # live AQS; network required
```

Frontend typecheck/build:

```bash
cd frontend
npm ci
npm run build
```

---

## Adding a Wikimedia project

1. Add `config/projects/<id>.yaml` (see [docs/PROJECT_CONFIGURATION.md](docs/PROJECT_CONFIGURATION.md)).
2. Add metrics only if needed in `config/metrics/catalog.yaml`.
3. Reload: `python -m app.jobs.cli seed-registry` or `collect-health` (reloads YAML by default).
4. Ingest: `bootstrap` / `ingest` / `daily` / `collect-replicas` as appropriate.
5. Do **not** hard-code project IDs or language-specific logic in collectors.

---

## Code principles

1. **Multi-project by config** — default workspace may be `fa.wikipedia`; logic must not assume it.  
2. **Official sources for activity** — prefer AQS; do not invent competing edit/editor counts.  
3. **Document every metric** — catalog fields + methodology notes.  
4. **Aggregates only** — no individual volunteer scoreboards.  
5. **UTC periods** — storage and API boundaries in UTC.  
6. **Load safety** — caps, statement timeouts, lag gates on replicas.  
7. **Secrets out of git** — env only; never log passwords.

Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Pull requests

1. Branch from `main`.  
2. Keep PRs focused; update docs when behavior or deploy steps change.  
3. If you change the SPA, commit a fresh `frontend` build under `backend/app/static`.  
4. Run `pytest -q` (and frontend build if you touched UI).  
5. Describe **what** and **why**; link issues if any.  

### Doc map

- Fresh Toolforge deploy: [docs/DEPLOY.md](docs/DEPLOY.md)  
- Full doc index: [docs/README.md](docs/README.md)  

Please do **not** reintroduce parallel “step-by-step” vs “reference” Toolforge guides with conflicting commands.

---

## Code of conduct

Be respectful to collaborators and to the Wikimedia communities this software measures. Treat operational data as a responsibility, not a scoreboard.
