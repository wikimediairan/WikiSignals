# WikiSignals — Toolforge deployment

Up-to-date guide for hosting this app on [Toolforge](https://wikitech.wikimedia.org/wiki/Portal:Toolforge) with **ToolsDB**, **scheduled daily jobs**, and **wiki replicas** — without putting unsafe load on shared infrastructure.

**Prefer the numbered walkthrough:** [TOOLFORGE_STEP_BY_STEP.md](TOOLFORGE_STEP_BY_STEP.md)

Also see: [SECURITY.md](SECURITY.md), [DATA_COLLECTION.md](DATA_COLLECTION.md).

**Deploy with the official Python buildpack** ([docs](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Building_container_images/My_first_Buildpack_Python_tool)):

- Root `requirements.txt`, `Procfile`, `.python-version` (no root Dockerfile)
- `web: gunicorn --chdir=backend ... app.main:app`
- Start: `toolforge webservice buildservice start --mount=none`

---

## Architecture on Toolforge

| Component | Role |
|-----------|------|
| **Webservice** (buildservice image) | FastAPI + committed SPA static files |
| **ToolsDB** | Aggregate metrics, snapshots, job ledger |
| **Daily job** | `python -m app.jobs.cli daily` — budgeted AQS + MW + optional replicas |
| **Wiki replicas** | Read-only analytics MySQL for reverts / active admins (aggregate SQL only) |
| **AQS / MediaWiki API** | Official context + categoryinfo + capped logevents |

```
Browser → https://YOURTOOL.toolforge.org
              │
              ▼
         FastAPI webservice ──reads──► ToolsDB (aggregates)
              ▲
         daily job ──writes──┘
              │
     ┌────────┼──────────────┐
     ▼        ▼              ▼
   AQS    MW Action API   Wiki replicas
 (context) (light)      (bounded SQL)
```

---

## Prerequisites

1. [Wikimedia developer account](https://wikitech.wikimedia.org/wiki/Help:Create_a_Wikimedia_developer_account)
2. Tool account on [toolsadmin.wikimedia.org](https://toolsadmin.wikimedia.org/) (example name: `wikisignals`)
3. Git remote (GitHub repo recommended (`wikimediairan/WikiSignals`))
4. Toolforge membership / ability to `become YOURTOOL`

---

## 1. Create ToolsDB database

```bash
ssh login.toolforge.org
become YOURTOOL

# Interactive ToolsDB shell
sql tools
```

```sql
CREATE DATABASE sXXXXX__wikisignals
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- Replace sXXXXX with your tool login name (e.g. s56000)
```

Credentials for ToolsDB are available via:

```bash
# Toolforge documents toolsdb credentials under tool home;
# typical pattern after sql tools / maintain-dbusers:
cat ~/replica.my.cnf   # may include user/password used for both replicas and toolsdb variants
```

Set `DATABASE_URL` (async driver):

```text
mysql+aiomysql://USER:PASSWORD@tools.db.svc.wikimedia.cloud:3306/sXXXXX__wikisignals
```

Use **ToolsDB primary** for writes from jobs and the webservice. For long ad-hoc analytics against ToolsDB itself you may use the ToolsDB read replica host (`tools-readonly.db.svc.wikimedia.cloud`) — not required for this app.

---

## 2. Environment variables

```bash
become YOURTOOL

# REQUIRED — real contact URL or email (403 without this)
toolforge envvars create USER_AGENT \
  "CommunityHealthObservatory/0.1 (https://YOURTOOL.toolforge.org; you@example.org)"

toolforge envvars create APP_NAME "Wikimedia Community Health Observatory"
toolforge envvars create ENVIRONMENT "production"
toolforge envvars create DOCS_ENABLED "false"
toolforge envvars create DEFAULT_PROJECT_ID "fa.wikipedia"
toolforge envvars create FRONTEND_URL "https://YOURTOOL.toolforge.org"
toolforge envvars create CORS_ORIGINS "https://YOURTOOL.toolforge.org"

# ToolsDB
toolforge envvars create DATABASE_URL "mysql+aiomysql://USER:PASS@tools.db.svc.wikimedia.cloud:3306/sXXXXX__wikisignals"

# Polite HTTP pacing (seconds between outbound Wikimedia requests)
toolforge envvars create HTTP_MIN_INTERVAL_SECONDS "0.75"
toolforge envvars create HTTP_MAX_RETRIES "5"

# Daily job budgets (defaults are conservative)
toolforge envvars create DAILY_MAX_PROJECTS "4"
toolforge envvars create DAILY_AQS_LOOKBACK_MONTHS "3"
toolforge envvars create DAILY_ADMIN_LOG_DAYS "35"
toolforge envvars create DAILY_ADMIN_LOG_MAX_PAGES "8"
toolforge envvars create DAILY_PROJECT_PAUSE_SECONDS "3"
toolforge envvars create DAILY_USE_MEDIAWIKI_LOGS "true"
toolforge envvars create DAILY_USE_REPLICAS "true"
```

### Wiki replicas (recommended on Toolforge)

Credentials usually come from `~/replica.my.cnf` after replica access is provisioned for the tool.

```bash
# Example — use the analytics replica endpoint for a wiki section, or the
# pattern documented for your tool account. Hostnames look like:
#   fawiki.analytics.db.svc.wikimedia.cloud
# User/password from replica.my.cnf ([client] section).

toolforge envvars create WIKI_REPLICAS_ENABLED "true"
toolforge envvars create WIKI_REPLICAS_HOST "fawiki.analytics.db.svc.wikimedia.cloud"
toolforge envvars create WIKI_REPLICAS_USER "sXXXXX"
toolforge envvars create WIKI_REPLICAS_PASSWORD "…"
toolforge envvars create WIKI_REPLICAS_PORT "3306"
toolforge envvars create WIKI_REPLICAS_MAX_STATEMENT_TIME "30"
toolforge envvars create WIKI_REPLICAS_MAX_LAG_SECONDS "600"
```

**Never commit** replica or ToolsDB passwords to git. Envvars only.

---

## 3. Build frontend into the backend image

Toolforge buildservice is most reliable when SPA assets are **committed**:

```bash
# On your laptop
cd frontend
npm ci
npm run build   # → backend/app/static/

git add backend/app/static
git commit -m "Build frontend for Toolforge"
git push
```

Confirm `/health` reports `"frontend": "built"` after deploy.

---

## 4. Build and start the webservice

From the tool account (after the repo is available to the build service):

```bash
become YOURTOOL

toolforge build start https://github.com/wikimediairan/WikiSignals.git
# wait until build succeeds

toolforge webservice buildservice start --mount=none
# or: toolforge webservice restart --mount=none
```

Dockerfile CMD uses uvicorn/gunicorn; ensure `PORT` is honored if your image wrapper sets it. This repo’s `backend/gunicorn.conf.py` binds `0.0.0.0:$PORT`.

Health check:

```bash
curl -sS https://YOURTOOL.toolforge.org/health
# {"status":"ok","service":"wikisignals","frontend":"built",...}
```

---

## 5. One-time bootstrap (history + registry)

Run **once** (or after major metric catalog changes). Heavier than the daily job — **do not** schedule multi-year bootstrap every day.

Use **Procfile** command names (buildpack image):

```bash
# ~2 years AQS
toolforge jobs run wikisignals-bootstrap \
  --image tool-wikisignals/tool-wikisignals:latest \
  --command "bootstrap" \
  --wait --timeout 7200 --emails onfailure

# ~5 years AQS (60 months) — once only
toolforge jobs run wikisignals-bootstrap-5y \
  --image tool-wikisignals/tool-wikisignals:latest \
  --command "bootstrap-5y" \
  --wait --timeout 14400 --emails onfailure

# Or explicit since-date ingest:
toolforge jobs run wikisignals-ingest-5y \
  --image tool-wikisignals/tool-wikisignals:latest \
  --command "ingest-5y" \
  --wait --timeout 14400 --emails onfailure

# Maintenance snapshots + recent admin logs
toolforge jobs run wikisignals-health-init \
  --image tool-wikisignals/tool-wikisignals:latest \
  --command "collect-health" \
  --wait --timeout 3600 --emails onfailure
```

---

## 6. Daily scheduled job (preferred)

The **`daily`** command is designed to stay light:

| Step | Budget |
|------|--------|
| AQS | Only last **3 months** (not full history) |
| Maintenance | One `categoryinfo` call per **enabled** track |
| Admin logs | Last **~35 days**, **≤8** API pages per log type |
| Replicas | Lag gate + **30s** max statement time; aggregate SQL only |
| Projects | At most **DAILY_MAX_PROJECTS** (default 4–8) |
| Between projects | Pause **2–3s** |

```bash
toolforge jobs run wikisignals-daily \
  --image tool-YOURTOOL/tool-YOURTOOL:latest \
  --command "python -m app.jobs.cli daily" \
  --schedule "17 3 * * *" \
  --emails onfailure \
  --timeout 1800
```

Notes:

- Prefer a **quiet UTC hour** (example: 03:17 UTC) to reduce collision with other tools.
- Start with **one project** (`daily --project fa.wikipedia`) for the first week.
- Watch emails / `toolforge jobs list` / job logs after the first few runs.

Manual:

```bash
python -m app.jobs.cli daily --project fa.wikipedia
python -m app.jobs.cli check-connectivity
```

---

## 7. Load & replica safety (do not get blocked)

### Principles

1. **Prefer AQS** for official activity series (edits, editors, pageviews). Do not re-scan all revisions for those.
2. **Prefer categoryinfo** for backlog size (cheap) over listing every category member daily.
3. **Prefer replicas** for bulk historical aggregates over hammering Action API logevents.
4. **Never** dump user-level contribution graphs into ToolsDB for public dashboards.
5. **Cap** project count, time windows, and statement duration.

### What the daily job does *not* do

- Full multi-year AQS backfill every night  
- Unlimited logevents pagination  
- Unbounded `SELECT * FROM revision`  
- Parallel replica storms across all wikis  

### If you see rate limits / lag

| Symptom | Action |
|---------|--------|
| HTTP 429/403 from AQS/MW | Raise `HTTP_MIN_INTERVAL_SECONDS` to `1`–`2`; reduce `DAILY_MAX_PROJECTS` |
| Replica lag skip messages | Job skips replica step when lag &gt; `WIKI_REPLICAS_MAX_LAG_SECONDS` — wait for next day |
| Job timeout | Lower `DAILY_ADMIN_LOG_MAX_PAGES`; disable MW logs (`DAILY_USE_MEDIAWIKI_LOGS=false`) and rely on replicas |
| ToolsDB pressure | Ensure only one daily job; no overlapping schedules |

### Multi-wiki growth

Add projects only after fa.wikipedia is stable for weeks. Raise `DAILY_MAX_PROJECTS` gradually. Consider **one job per wiki** with staggered schedules if needed.

---

## 8. Config updates on Toolforge

Project health tracks live in `config/projects/*.yaml` inside the image.

1. Edit YAML in git  
2. Rebuild image / redeploy  
3. Next `daily` run reloads registry from YAML automatically  

Or run:

```bash
python -m app.jobs.cli collect-health --project fa.wikipedia
```

(`--reload-config` is default.)

---

## 9. Operational checklist

- [ ] `USER_AGENT` has real contact  
- [ ] `DOCS_ENABLED=false` in production  
- [ ] `CORS_ORIGINS` is only your tool URL  
- [ ] ToolsDB URL uses `sXXXXX__wikisignals`  
- [ ] Frontend built into `backend/app/static`  
- [ ] Bootstrap run once  
- [ ] Daily job scheduled, not full bootstrap  
- [ ] Replica env set **or** `DAILY_USE_REPLICAS=false` until ready  
- [ ] `/health` OK  
- [ ] First daily job log reviewed  

---

## 10. Troubleshooting

### 403 from Wikimedia APIs

Almost always User-Agent. Run:

```bash
python -m app.jobs.cli check-connectivity
```

### Empty maintenance tracks

YAML not reloaded or `enabled: false`. After editing YAML, redeploy and run `collect-health` / `daily`.

### Webservice 502

Check build logs, ensure static frontend exists, confirm `DATABASE_URL` and migrations (`alembic upgrade head`).

---

## 11. Related docs

- [SECURITY.md](SECURITY.md) — security review and production settings  
- [DATA_COLLECTION.md](DATA_COLLECTION.md) — load budgets and data sources  
- [PROJECT_CONFIGURATION.md](PROJECT_CONFIGURATION.md) — health tracks  
- [Wikitech: Running jobs](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Running_jobs)  
- [Wikitech: ToolsDB](https://wikitech.wikimedia.org/wiki/Help:Toolforge/ToolsDB)  
