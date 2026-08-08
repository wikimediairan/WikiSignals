# Contributing to WikiSignals

Thank you for helping improve WikiSignals — community health and capacity analytics for Wikimedia.

**Source:** https://github.com/wikimediairan/WikiSignals

## Development setup

```bash
cp .env.example .env
# set USER_AGENT with a real contact

docker compose up --build
# API: http://localhost:8000
# SPA: http://localhost:5173
```

Without Docker:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=sqlite+aiosqlite:///./wikisignals.db
export USER_AGENT="WikiSignals/0.1 (https://github.com/wikimediairan/WikiSignals; you@example.org)"
export PYTHONPATH=.
alembic upgrade head
python -m app.jobs.cli bootstrap --project fa.wikipedia --months 12
uvicorn app.main:app --reload
```

```bash
cd frontend && npm install && npm run dev
```

## Tests

```bash
cd backend
pytest -q
pytest -m smoke   # live AQS; network required
```

## Adding a Wikimedia project

1. Add `config/projects/<id>.yaml`.
2. Run `python -m app.jobs.cli seed-registry` or `collect-health` (reloads YAML).
3. Run ingest / daily for that project.

## Code principles

- Do not hard-code Persian Wikipedia into metric logic  
- Prefer official Wikimedia data sources for activity context  
- Document metric methodology for every new metric  
- Aggregate analytics only; no individual volunteer scoreboards  
- UTC for storage and API period boundaries  

## License

Contributions are accepted under GNU GPL v3 or later.
