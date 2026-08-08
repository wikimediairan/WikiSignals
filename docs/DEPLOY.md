# Deploy WikiSignals on Toolforge

End-to-end guide to stand up a **fresh** instance with the Toolforge **Python buildpack**.  
This is the only Toolforge deploy document — older split guides were removed.

Upstream docs:

- [Buildpack Python tools](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Building_container_images/My_first_Buildpack_Python_tool)
- [ToolsDB](https://wikitech.wikimedia.org/wiki/Help:Toolforge/ToolsDB)
- [Jobs framework](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Jobs_framework)

Replace `YOURTOOL` / `sXXXXX` with your tool name and DB user (from `~/replica.my.cnf`).

---

## How it fits together

| Piece | Role |
|-------|------|
| **Buildpack image** | Root `requirements.txt` + `Procfile` + `.python-version` (no root Dockerfile) |
| **Webservice** | FastAPI + SPA static files → `https://YOURTOOL.toolforge.org` |
| **ToolsDB** | Aggregate metrics (`sXXXXX__wikisignals`) |
| **Jobs** | One-off bootstrap + scheduled `daily` |
| **Wiki replicas** | Optional; required for conflict metrics (reverts) |

```
Browser → webservice (FastAPI + SPA) ──reads──► ToolsDB
                    ▲
              jobs write ─┘
                    │
         AQS · MediaWiki API · wiki replicas
```

**Do not set `CONFIG_DIR=/config`.** That path was for an old Docker layout. On the buildpack image, YAML lives at `/workspace/config` inside the git tree.

---

## Prerequisites

1. [Wikimedia developer account](https://wikitech.wikimedia.org/wiki/Help:Create_a_Wikimedia_developer_account)
2. A Toolforge tool ([toolsadmin](https://toolsadmin.wikimedia.org/)), e.g. `wikisignals`
3. Public git remote the build service can clone (e.g. GitHub `wikimediairan/WikiSignals`)
4. SSH: `ssh login.toolforge.org` then `become YOURTOOL`

Repo layout the buildpack expects:

```text
WikiSignals/
  Procfile
  requirements.txt
  .python-version
  service.template
  config/projects/*.yaml
  backend/          # app + alembic
  frontend/         # build output → backend/app/static
  backend/Dockerfile   # local docker-compose only — ignored by Toolforge
```

---

## 1. Create ToolsDB

```bash
become YOURTOOL
sql tools
```

```sql
CREATE DATABASE sXXXXX__wikisignals
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

`TOOL_TOOLSDB_USER` / `TOOL_TOOLSDB_PASSWORD` are usually injected automatically.  
WikiSignals builds `DATABASE_URL` from them if you do not set one explicitly.

---

## 2. Environment variables

```bash
become YOURTOOL

# REQUIRED — real contact or Wikimedia blocks with 403
toolforge envvars create USER_AGENT \
  "WikiSignals/0.1 (https://github.com/wikimediairan/WikiSignals; you@example.org)"

toolforge envvars create APP_NAME "WikiSignals"
toolforge envvars create ENVIRONMENT "production"
toolforge envvars create DOCS_ENABLED "false"
toolforge envvars create DEFAULT_PROJECT_ID "fa.wikipedia"
toolforge envvars create FRONTEND_URL "https://YOURTOOL.toolforge.org"
toolforge envvars create CORS_ORIGINS "https://YOURTOOL.toolforge.org"

toolforge envvars create HTTP_MIN_INTERVAL_SECONDS "0.75"
toolforge envvars create DAILY_MAX_PROJECTS "2"
toolforge envvars create DAILY_USE_REPLICAS "true"

# Optional explicit DB (skip if TOOL_TOOLSDB_* is enough):
# toolforge envvars create DATABASE_URL \
#   "mysql+aiomysql://sXXXXX:PASS@tools.db.svc.wikimedia.cloud:3306/sXXXXX__wikisignals"
```

### Wiki replicas (conflict / reverts)

Credentials: `cat ~/replica.my.cnf` on the tool account.

```bash
toolforge envvars create WIKI_REPLICAS_ENABLED "true"
toolforge envvars create WIKI_REPLICAS_HOST "fawiki.analytics.db.svc.wikimedia.cloud"
toolforge envvars create WIKI_REPLICAS_USER "sXXXXX"
toolforge envvars create WIKI_REPLICAS_PASSWORD "…"
toolforge envvars create WIKI_REPLICAS_PORT "3306"
toolforge envvars create WIKI_REPLICAS_MAX_STATEMENT_TIME "30"
toolforge envvars create WIKI_REPLICAS_MAX_LAG_SECONDS "600"
```

Env vars alone do **not** fill reverts. You must run `collect-replicas` (or `daily` for ~3 months).  
`collect-health` uses the MediaWiki API only and does **not** write conflict series.

Never commit passwords. Never set `CONFIG_DIR`.

---

## 3. Frontend in the image

The SPA is served from `backend/app/static` (committed build artifacts).

On your laptop before the first deploy (and after UI changes):

```bash
cd frontend && npm ci && npm run build
git add backend/app/static
git commit -m "Build frontend"
git push
```

---

## 4. Build and start the webservice

```bash
become YOURTOOL

toolforge build start https://github.com/wikimediairan/WikiSignals.git
toolforge build show
# wait until Status: ok

toolforge webservice buildservice start --mount=none
toolforge webservice status
curl -sS https://YOURTOOL.toolforge.org/health
```

Expect `"status":"ok"`, `"service":"wikisignals"`, `"frontend":"built"`.

Use **buildservice** only. Plain `webservice start` looks for lighttpd/`public_html`.

---

## 5. Jobs: image and names

Procfile process names (passed as `--command`):

| Command | Purpose |
|---------|---------|
| `diagnose` | Config/DB/replicas status (no secrets) |
| `migrate` | Alembic migrations |
| `seed` | Load projects + metrics from YAML |
| `check` | Probe AQS + MediaWiki with `USER_AGENT` |
| `bootstrap` | Seed + ~24 months AQS for `fa.wikipedia` |
| `bootstrap-5y` | Seed + ~60 months AQS (once) |
| `ingest-5y` | AQS only from 2021-01-01 |
| `collect-health` | Maintenance / processes / admin logs (MW API) |
| `collect-replicas` | Reverts + active admins (~24 months) |
| `daily` | Light incremental update |

Image name is usually `tool-YOURTOOL/tool-YOURTOOL:latest`.

**Job names are unique** and stay after completion. Re-run:

```bash
toolforge jobs delete JOBNAME   # ignore error if missing
toolforge jobs run JOBNAME ...
```

One-off jobs: use `--wait`, **not** `--timeout` (timeout is for scheduled jobs only).

---

## 6. First-time data load

```bash
IMG=tool-YOURTOOL/tool-YOURTOOL:latest

toolforge jobs delete wikisignals-diagnose 2>/dev/null || true
toolforge jobs run wikisignals-diagnose \
  --image "$IMG" --command "diagnose" --wait --emails onfailure
toolforge jobs logs wikisignals-diagnose
# Expect: project_yaml_count >= 1, database_url_host with tools.db
# If replicas configured: wiki_replicas_ready=True

toolforge jobs delete wikisignals-migrate 2>/dev/null || true
toolforge jobs run wikisignals-migrate \
  --image "$IMG" --command "migrate" --wait --emails onfailure

toolforge jobs delete wikisignals-seed 2>/dev/null || true
toolforge jobs run wikisignals-seed \
  --image "$IMG" --command "seed" --wait --emails onfailure
# Expect: projects count > 0 (seed exits 1 if 0)

toolforge jobs delete wikisignals-check 2>/dev/null || true
toolforge jobs run wikisignals-check \
  --image "$IMG" --command "check" --wait --emails onfailure

curl -sS https://YOURTOOL.toolforge.org/api/v1/projects
```

### Official activity (AQS) — once

```bash
# ~2 years (recommended first run)
toolforge jobs delete wikisignals-bootstrap 2>/dev/null || true
toolforge jobs run wikisignals-bootstrap \
  --image "$IMG" --command "bootstrap" --wait --emails onfailure

# Or ~5 years (heavy; do not schedule daily)
# toolforge jobs run wikisignals-bootstrap-5y --image "$IMG" --command "bootstrap-5y" --wait
```

On 403/429, wait and re-run — upserts are safe.

### Maintenance / admin logs

```bash
toolforge jobs delete wikisignals-health 2>/dev/null || true
toolforge jobs run wikisignals-health \
  --image "$IMG" --command "collect-health" --wait --emails onfailure
```

Requires enabled tracks with real categories in `config/projects/*.yaml`.  
See [PROJECT_CONFIGURATION.md](PROJECT_CONFIGURATION.md).

### Conflict metrics (replicas)

```bash
toolforge jobs delete wikisignals-replicas 2>/dev/null || true
toolforge jobs run wikisignals-replicas \
  --image "$IMG" --command "collect-replicas" --wait --emails onfailure
toolforge jobs logs wikisignals-replicas
# Expect: reverts points upserted, done: reverts_points=…
```

---

## 7. Schedule daily updates

Do **not** schedule bootstrap/ingest-5y. Only `daily`:

```bash
toolforge jobs delete wikisignals-daily 2>/dev/null || true
toolforge jobs run wikisignals-daily \
  --image "$IMG" \
  --command "daily" \
  --schedule "17 3 * * *" \
  --timeout 1800 \
  --emails onfailure
```

Daily budget (defaults): last ~3 months AQS, current category snapshots, short admin-log window, optional replica aggregates. Details: [DATA_COLLECTION.md](DATA_COLLECTION.md).

---

## 8. After code changes

```bash
# laptop (if UI changed)
cd frontend && npm ci && npm run build
git add backend/app/static && git commit -m "Build frontend" && git push

# bastion
toolforge build start https://github.com/wikimediairan/WikiSignals.git
# wait until ok
toolforge webservice buildservice restart --mount=none
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Project not found` / seed `projects: 0` | Unset `CONFIG_DIR`; rebuild; re-run `seed` |
| `A job with the name … already exists` | `toolforge jobs delete NAME` then re-run |
| `gunicorn` / `python` not found | Use buildpack layout (root `requirements.txt`); no root Dockerfile |
| `no healthy upstream` / 502 | `toolforge webservice logs`; build status; DB env |
| AQS/MW 403 | Real `USER_AGENT`; run `check` |
| Empty maintenance | Enable tracks with real categories; re-run `collect-health` |
| Empty reverts | Replicas env + `collect-replicas`; not `collect-health` |
| Replica auth error | USER/PASSWORD from `~/replica.my.cnf` |
| Replica lag skip | Wait or carefully raise `WIKI_REPLICAS_MAX_LAG_SECONDS` |

Debug shell:

```bash
toolforge webservice buildservice shell
# then: launcher bash
which python gunicorn
ls /workspace
```

---

## Production checklist

- [ ] `USER_AGENT` has a real contact  
- [ ] `ENVIRONMENT=production`, `DOCS_ENABLED=false`  
- [ ] `CORS_ORIGINS` is only your tool URL  
- [ ] ToolsDB `sXXXXX__wikisignals` created  
- [ ] Frontend built into `backend/app/static`  
- [ ] `migrate` + `seed` OK (`project_yaml_count` / projects &gt; 0)  
- [ ] Bootstrap (or ingest) once  
- [ ] `collect-health` if tracks enabled  
- [ ] `collect-replicas` if conflict metrics needed  
- [ ] `daily` scheduled (not bootstrap)  
- [ ] `/health` OK  

Security notes: [SECURITY.md](SECURITY.md).
