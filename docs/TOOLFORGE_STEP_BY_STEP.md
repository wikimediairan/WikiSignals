# Toolforge deployment — step by step (Python **buildpack**)

Deploy **WikiSignals** using the official Toolforge **Build Service + Python buildpack**  
(see [My first Buildpack Python tool](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Building_container_images/My_first_Buildpack_Python_tool)).

**Do not use a root Dockerfile.** Toolforge detects Python via:

| File | Role |
|------|------|
| `requirements.txt` | Python deps (at **repo root**) |
| `Procfile` | `web:` start command + job commands |
| `.python-version` | Python 3.12 |
| `service.template` | `type: buildservice`, `mount: none` |

Source: https://github.com/wikimediairan/WikiSignals

Replace `sXXXXX` with your tool DB user (from `replica.my.cnf`).

---

## 1. Accounts

1. Wikimedia developer account + [Toolforge tool](https://toolsadmin.wikimedia.org/) named e.g. `wikisignals`
2. SSH: `ssh login.toolforge.org` then `become wikisignals`

---

## 2. ToolsDB

```bash
sql tools
```

```sql
CREATE DATABASE sXXXXX__wikisignals
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

---

## 3. Envvars

Toolforge injects `TOOL_TOOLSDB_USER` / `TOOL_TOOLSDB_PASSWORD` automatically.  
WikiSignals will build `DATABASE_URL` from them if you do not set one.

Still set:

```bash
become wikisignals

toolforge envvars create USER_AGENT \
  "WikiSignals/0.1 (https://github.com/wikimediairan/WikiSignals; you@example.org)"

toolforge envvars create APP_NAME "WikiSignals"
toolforge envvars create ENVIRONMENT "production"
toolforge envvars create DOCS_ENABLED "false"
toolforge envvars create DEFAULT_PROJECT_ID "fa.wikipedia"
toolforge envvars create FRONTEND_URL "https://wikisignals.toolforge.org"
toolforge envvars create CORS_ORIGINS "https://wikisignals.toolforge.org"

# Optional explicit DB (otherwise auto from TOOL_TOOLSDB_*):
# toolforge envvars create DATABASE_URL \
#   "mysql+aiomysql://sXXXXX:PASS@tools.db.svc.wikimedia.cloud:3306/sXXXXX__wikisignals"

toolforge envvars create HTTP_MIN_INTERVAL_SECONDS "0.75"
toolforge envvars create DAILY_MAX_PROJECTS "2"
```

Replicas (optional later):

```bash
toolforge envvars create WIKI_REPLICAS_ENABLED "true"
toolforge envvars create WIKI_REPLICAS_HOST "fawiki.analytics.db.svc.wikimedia.cloud"
# user/password auto from TOOL_REPLICA_* if set by Toolforge
```

---

## 4. Build (from public GitHub)

```bash
toolforge build start https://github.com/wikimediairan/WikiSignals.git
toolforge build show
# wait until Status: ok
```

---

## 5. Start webservice

```bash
# Always use buildservice (plain "webservice start" looks for public_html / lighttpd)
toolforge webservice buildservice start --mount=none
```

```bash
toolforge webservice status
toolforge webservice logs
# logs should say: Using worker: uvicorn.workers.UvicornWorker
# NOT: Using worker: sync

curl -sS https://wikisignals.toolforge.org/health
```

Expect `"status":"ok"` and `"service":"wikisignals"`.

---

## 6. Migrate + seed (jobs use Procfile entries)

> **Note:** On current Toolforge, `--timeout` is only valid for **scheduled** jobs (`--schedule`). One-shot jobs use `--wait` without `--timeout`.

Image name is usually `tool-wikisignals/tool-wikisignals:latest`.

```bash
toolforge jobs run wikisignals-migrate \
  --image tool-wikisignals/tool-wikisignals:latest \
  --command "migrate" \
  --wait --emails onfailure

toolforge jobs run wikisignals-seed \
  --image tool-wikisignals/tool-wikisignals:latest \
  --command "seed" \
  --wait --emails onfailure

toolforge jobs run wikisignals-check \
  --image tool-wikisignals/tool-wikisignals:latest \
  --command "check" \
  --wait --emails onfailure
```

---

## 7. One-time data load

### 7a. Official activity context from AQS (choose one)

**~2 years (safer first run):**

```bash
toolforge jobs run wikisignals-bootstrap \
  --image tool-wikisignals/tool-wikisignals:latest \
  --command "bootstrap" \
  --wait --emails onfailure
```

**~5 years (60 months of AQS — once, not daily):**

```bash
# Seeds registry if needed + pulls monthly AQS for fa.wikipedia (~60 months)
toolforge jobs run wikisignals-bootstrap-5y \
  --image tool-wikisignals/tool-wikisignals:latest \
  --command "bootstrap-5y" \
  --wait --emails onfailure
```

Or, if migrate + seed already succeeded and you only need AQS points:

```bash
# From 2021-01-01 to now (about 5 years depending on current date)
toolforge jobs run wikisignals-ingest-5y \
  --image tool-wikisignals/tool-wikisignals:latest \
  --command "ingest-5y" \
  --wait --emails onfailure
```

Use a real `USER_AGENT`. If you hit 403/429, wait and re-run — upserts are safe to retry.

**What 5-year AQS gives you:** edits, active editors, pageviews, new pages, bot share inputs, etc.

**What it does *not* give:** multi-year maintenance backlog history (categoryinfo is current size only; history builds from daily snapshots going forward). Admin log depth via API is still limited; use replicas later for deep admin/revert history.

### 7b. Maintenance + admin logs (current / recent)

```bash
toolforge jobs run wikisignals-health \
  --image tool-wikisignals/tool-wikisignals:latest \
  --command "collect-health" \
  --wait --emails onfailure
```

---

## 8. Daily job

**Do not** schedule `bootstrap-5y` or `ingest-5y` daily. Only the light job:

```bash
toolforge jobs run wikisignals-daily \
  --image tool-wikisignals/tool-wikisignals:latest \
  --command "daily" \
  --schedule "17 3 * * *" \
  --timeout 1800 \
  --emails onfailure
```

Daily only refreshes ~3 months of AQS + current maintenance snapshots + short admin log window.

---

## 9. After code changes

```bash
# laptop: if UI changed
cd frontend && npm ci && npm run build
git add backend/app/static && git commit -m "Build frontend" && git push

# bastion
toolforge build start https://github.com/wikimediairan/WikiSignals.git
toolforge webservice restart
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `gunicorn: command not found` | Ensure **no root Dockerfile** (buildpack installs gunicorn from root `requirements.txt`) |
| `/usr/local/bin/python: No such file` | Same — you were on a custom Docker image; use buildpack layout |
| `no healthy upstream` | `toolforge webservice logs`; check build ok + envvars |
| Wrong DB | Create `sXXXXX__wikisignals`; check TOOL_TOOLSDB_* |
| Jobs fail | Use Procfile command names: `migrate`, `daily`, not raw shell unless wrapped |

Debug shell:

```bash
toolforge webservice buildservice shell
# inside:
launcher bash
which python gunicorn
ls
```

---

## Layout reminder (repo root)

```
WikiSignals/
  Procfile
  requirements.txt
  .python-version
  service.template
  config/
  backend/
    app/
    alembic/
  frontend/          # build → backend/app/static
  backend/Dockerfile # local docker-compose only (NOT used by Toolforge buildpack)
```
