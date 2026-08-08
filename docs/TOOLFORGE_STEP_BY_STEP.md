# Toolforge deployment — step by step

Deploy **WikiSignals** (community health and capacity analytics for Wikimedia) on Toolforge.

Source: https://github.com/wikimediairan/WikiSignals

Replace:

| Placeholder | Example |
|-------------|---------|
| `YOURTOOL` | `community-health` |
| `sXXXXX` | your tool DB user, e.g. `s56000` |
| `you@example.org` | a real email you read |

Official background: [Portal:Toolforge](https://wikitech.wikimedia.org/wiki/Portal:Toolforge), [Running jobs](https://wikitech.wikimedia.org/wiki/Help:Toolforge/Running_jobs), [ToolsDB](https://wikitech.wikimedia.org/wiki/Help:Toolforge/ToolsDB).

---

## Overview (what you will end up with)

1. **Webservice** at `https://YOURTOOL.toolforge.org` (API + UI)  
2. **ToolsDB** holding aggregates  
3. **One-time bootstrap** (history, e.g. months of AQS)  
4. **Daily job** (`python -m app.jobs.cli daily`) — light incremental updates  
5. Optional **wiki replicas** for reverts / active admins  

Do **not** schedule full multi-year bootstrap every day.

---

## Phase A — One-time accounts & repo

### Step 1 — Wikimedia developer account

1. Create account: https://wikitech.wikimedia.org/wiki/Help:Create_a_Wikimedia_developer_account  
2. Join Toolforge via [toolsadmin](https://toolsadmin.wikimedia.org/).

### Step 2 — Create the tool

1. Open https://toolsadmin.wikimedia.org/  
2. Create a new tool, e.g. `YOURTOOL`.  
3. Note the tool name and ToolsDB user prefix (`sXXXXX`).

### Step 3 — Put the code where Toolforge can build it

Preferred: [GitLab toolforge-repos](https://wikitech.wikimedia.org/wiki/Help:Toolforge/GitLab):

```text
https://gitlab.wikimedia.org/toolforge-repos/YOURTOOL
```

Push this repository (including root `Dockerfile`, `backend/`, `config/`, and built frontend).

### Step 4 — Build the frontend **on your laptop** and commit it

Toolforge often will not run a full Node build reliably. Commit the SPA into the image:

```bash
cd /path/to/observatory
cd frontend
npm ci
npm run build
# writes to backend/app/static/

cd ..
git add backend/app/static
git status   # should show index.html + assets/
git commit -m "Build frontend for Toolforge"
git push
```

Confirm locally:

```bash
ls backend/app/static/index.html backend/app/static/assets/
```

---

## Phase B — Log into Toolforge and prepare the tool home

### Step 5 — SSH and become the tool

```bash
ssh login.toolforge.org
become YOURTOOL
pwd
# should be something like /data/project/YOURTOOL
```

### Step 6 — Create ToolsDB database

```bash
sql tools
```

In the MySQL prompt:

```sql
CREATE DATABASE sXXXXX__observatory
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- use YOUR real sXXXXX (same as tool user)
SHOW DATABASES LIKE '%observatory%';
EXIT;
```

### Step 7 — Read DB / replica credentials

```bash
cat ~/replica.my.cnf
```

You typically get:

```ini
[client]
user = sXXXXX
password = ...
```

ToolsDB host for the app:

```text
tools.db.svc.wikimedia.cloud
```

Wiki analytics replica host for Persian Wikipedia (example):

```text
fawiki.analytics.db.svc.wikimedia.cloud
```

(Other wikis use other `*.analytics.db.svc.wikimedia.cloud` hosts.)

---

## Phase C — Environment variables

Run these as the tool user (`become YOURTOOL`).  
Use `toolforge envvars create` for new keys; `toolforge envvars update` if they already exist.

### Step 8 — Required app settings

```bash
# MUST be a real contact URL or email — otherwise Wikimedia APIs return 403
toolforge envvars create USER_AGENT \
  "WikiSignals/0.1 (https://github.com/wikimediairan/WikiSignals; you@example.org)"

toolforge envvars create APP_NAME "WikiSignals"
toolforge envvars create ENVIRONMENT "production"
toolforge envvars create DOCS_ENABLED "false"
toolforge envvars create LOG_LEVEL "INFO"

toolforge envvars create DEFAULT_PROJECT_ID "fa.wikipedia"
toolforge envvars create FRONTEND_URL "https://YOURTOOL.toolforge.org"
toolforge envvars create CORS_ORIGINS "https://YOURTOOL.toolforge.org"
toolforge envvars create CONFIG_DIR "/config"
```

### Step 9 — ToolsDB URL

```bash
# password from ~/replica.my.cnf (or maintain-dbusers docs for your tool)
toolforge envvars create DATABASE_URL \
  "mysql+aiomysql://sXXXXX:PASSWORD@tools.db.svc.wikimedia.cloud:3306/sXXXXX__observatory"
```

### Step 10 — Polite HTTP pacing (daily + bootstrap)

```bash
toolforge envvars create HTTP_MIN_INTERVAL_SECONDS "0.75"
toolforge envvars create HTTP_MAX_RETRIES "5"
```

### Step 11 — Daily job budgets (safe defaults)

```bash
toolforge envvars create DAILY_MAX_PROJECTS "2"
toolforge envvars create DAILY_AQS_LOOKBACK_MONTHS "3"
toolforge envvars create DAILY_ADMIN_LOG_DAYS "35"
toolforge envvars create DAILY_ADMIN_LOG_MAX_PAGES "8"
toolforge envvars create DAILY_PROJECT_PAUSE_SECONDS "3"
toolforge envvars create DAILY_USE_MEDIAWIKI_LOGS "true"
toolforge envvars create DAILY_USE_REPLICAS "true"
```

Start with `DAILY_MAX_PROJECTS=1` or `2` if you only care about fa.wikipedia.

### Step 12 — Wiki replicas (recommended; can do after first webservice works)

```bash
toolforge envvars create WIKI_REPLICAS_ENABLED "true"
toolforge envvars create WIKI_REPLICAS_HOST "fawiki.analytics.db.svc.wikimedia.cloud"
toolforge envvars create WIKI_REPLICAS_USER "sXXXXX"
toolforge envvars create WIKI_REPLICAS_PASSWORD "PASSWORD_FROM_replica.my.cnf"
toolforge envvars create WIKI_REPLICAS_PORT "3306"
toolforge envvars create WIKI_REPLICAS_MAX_STATEMENT_TIME "30"
toolforge envvars create WIKI_REPLICAS_MAX_LAG_SECONDS "600"
```

If replicas are not ready yet:

```bash
toolforge envvars create WIKI_REPLICAS_ENABLED "false"
toolforge envvars create DAILY_USE_REPLICAS "false"
```

You still get AQS + maintenance category snapshots + capped admin logs.

List envvars:

```bash
toolforge envvars list
```

---

## Phase D — Build image and start webservice

### Step 13 — Build the container from Git

```bash
become YOURTOOL

toolforge build start https://gitlab.wikimedia.org/toolforge-repos/YOURTOOL.git
# wait until status is successful
toolforge build list
```

Root `Dockerfile` copies `backend/` + `config/` and sets `CONFIG_DIR=/config`.

### Step 14 — Start the webservice

```bash
toolforge webservice buildservice start
# later: toolforge webservice restart
toolforge webservice status
```

### Step 15 — Smoke-check the live tool

From your laptop or bastion:

```bash
curl -sS https://YOURTOOL.toolforge.org/health
```

Expect JSON roughly like:

```json
{
  "status": "ok",
  "service": "wikisignals",
  "frontend": "built",
  "default_project_id": "fa.wikipedia"
}
```

If `"frontend": "missing"`, redo Step 4 (commit static build) and rebuild.

Open in browser:

```text
https://YOURTOOL.toolforge.org/
```

API projects (after migrate + seed):

```bash
curl -sS https://YOURTOOL.toolforge.org/api/v1/projects | head
```

---

## Phase E — Database migrate + first data load

Jobs run **inside the built image**. Image name is usually:

```text
tool-YOURTOOL/tool-YOURTOOL:latest
```

Confirm with:

```bash
toolforge build list
# or toolforge jobs images
```

### Step 16 — Migrate schema + seed registry (no network-heavy ingest)

```bash
toolforge jobs run observatory-migrate \
  --image tool-YOURTOOL/tool-YOURTOOL:latest \
  --command "bash -lc 'alembic upgrade head && python -m app.jobs.cli seed-registry'" \
  --wait \
  --emails onfailure
```

If the job cannot find `alembic`, the workdir may differ; try:

```bash
--command "bash -lc 'cd /app && alembic upgrade head && python -m app.jobs.cli seed-registry'"
```

### Step 17 — Connectivity check (User-Agent)

```bash
toolforge jobs run observatory-ping \
  --image tool-YOURTOOL/tool-YOURTOOL:latest \
  --command "python -m app.jobs.cli check-connectivity" \
  --wait \
  --emails onfailure
```

Both AQS and MediaWiki must print `OK`. If 403: fix `USER_AGENT` (real email/URL), then `toolforge envvars update USER_AGENT "..."`.

### Step 18 — One-time AQS history (example: 24 or 60 months)

**Heavy — run once**, not daily.

```bash
# 24 months (safer first try)
toolforge jobs run observatory-bootstrap-aqs \
  --image tool-YOURTOOL/tool-YOURTOOL:latest \
  --command "python -m app.jobs.cli bootstrap --project fa.wikipedia --months 24" \
  --wait \
  --timeout 7200 \
  --emails onfailure
```

For ~5 years later (optional):

```bash
toolforge jobs run observatory-bootstrap-aqs-5y \
  --image tool-YOURTOOL/tool-YOURTOOL:latest \
  --command "python -m app.jobs.cli ingest --project fa.wikipedia --since 2021-01-01" \
  --wait \
  --timeout 14400 \
  --emails onfailure
```

Use a valid `USER_AGENT` and be patient if rate-limited.

### Step 19 — One-time health collection (maintenance + admin logs)

Requires maintenance tracks in `config/projects/fa.wikipedia.yaml` (`enabled: true` + real category). That config is **inside the image**, so edit git → rebuild → then:

```bash
toolforge jobs run observatory-health-init \
  --image tool-YOURTOOL/tool-YOURTOOL:latest \
  --command "python -m app.jobs.cli collect-health --project fa.wikipedia --months 2" \
  --wait \
  --timeout 3600 \
  --emails onfailure
```

### Step 20 — Verify data in the API

```bash
curl -sS "https://YOURTOOL.toolforge.org/api/v1/projects/fa.wikipedia/health" | head -c 800
curl -sS "https://YOURTOOL.toolforge.org/api/v1/projects/fa.wikipedia/backlogs" | head -c 800
curl -sS "https://YOURTOOL.toolforge.org/api/v1/projects/fa.wikipedia/metrics/editors.active?interval=month&start=2024-01-01&end=2026-01-01" | head -c 800
```

---

## Phase F — Schedule the light daily job

### Step 21 — Register daily update

```bash
toolforge jobs run observatory-daily \
  --image tool-YOURTOOL/tool-YOURTOOL:latest \
  --command "python -m app.jobs.cli daily --project fa.wikipedia" \
  --schedule "17 3 * * *" \
  --timeout 1800 \
  --emails onfailure
```

Meaning:

- Every day at **03:17 UTC**  
- Only **fa.wikipedia** (safest start)  
- AQS last **~3 months**, short admin log window, categoryinfo, optional replicas  
- Emails you on failure  

List / logs:

```bash
toolforge jobs list
toolforge jobs logs observatory-daily
```

### Step 22 — (Optional) expand later

When stable for a week:

```bash
# All enabled projects (still capped by DAILY_MAX_PROJECTS)
toolforge jobs delete observatory-daily
toolforge jobs run observatory-daily \
  --image tool-YOURTOOL/tool-YOURTOOL:latest \
  --command "python -m app.jobs.cli daily" \
  --schedule "17 3 * * *" \
  --timeout 1800 \
  --emails onfailure
```

---

## Phase G — Ongoing operations

### After you change project YAML (e.g. new maintenance category)

1. Edit `config/projects/fa.wikipedia.yaml` in git  
2. Commit + push  
3. `toolforge build start …`  
4. `toolforge webservice restart`  
5. Either wait for daily job, or:

```bash
toolforge jobs run observatory-reload \
  --image tool-YOURTOOL/tool-YOURTOOL:latest \
  --command "python -m app.jobs.cli collect-health --project fa.wikipedia --months 1" \
  --wait
```

(`collect-health` reloads YAML into ToolsDB by default.)

### After you change Python/Vue code

1. Rebuild frontend if UI changed; commit `backend/app/static`  
2. Push  
3. `toolforge build start …`  
4. `toolforge webservice restart`  
5. Re-run migrate if new Alembic revisions:  

```bash
toolforge jobs run observatory-migrate \
  --image tool-YOURTOOL/tool-YOURTOOL:latest \
  --command "alembic upgrade head" \
  --wait
```

### Useful commands

```bash
toolforge webservice status
toolforge webservice stop
toolforge webservice start
toolforge jobs list
toolforge jobs delete JOBNAME
toolforge envvars list
python -m app.jobs.cli check-connectivity   # inside a job
```

---

## Checklist (print and tick)

- [ ] Tool account created  
- [ ] Code on GitLab toolforge-repos  
- [ ] Frontend built and committed under `backend/app/static`  
- [ ] ToolsDB `sXXXXX__observatory` created  
- [ ] `USER_AGENT` real contact  
- [ ] `DATABASE_URL` set  
- [ ] `DOCS_ENABLED=false`, tight `CORS_ORIGINS`  
- [ ] Build succeeded  
- [ ] Webservice up; `/health` → `frontend: built`  
- [ ] `alembic upgrade head` + `seed-registry`  
- [ ] `check-connectivity` OK  
- [ ] One-time bootstrap AQS  
- [ ] One-time `collect-health`  
- [ ] API `/health` and `/backlogs` show data  
- [ ] Daily job scheduled (not bootstrap)  
- [ ] First daily log reviewed  

---

## Common failures

| Symptom | Fix |
|---------|-----|
| HTTP 403 from AQS/MW | Fix `USER_AGENT`; run `check-connectivity` |
| `frontend: missing` | Rebuild SPA, commit `backend/app/static`, rebuild image |
| Maintenance still `enabled: false` | Config only in DB after seed; rebuild image + `collect-health` |
| Job “command not found” | Prefix with `cd /app &&` or use absolute module path |
| Empty metrics | Bootstrap/ingest not run yet, or wrong `DATABASE_URL` |
| Replica errors | Set hosts/creds or `WIKI_REPLICAS_ENABLED=false` |
| Job timeout | Lower months/pages; use `daily` not full bootstrap |

---

## What not to do

1. **Do not** schedule `bootstrap --months 60` every day.  
2. **Do not** set `USER_AGENT` to `@localhost` or leave it empty.  
3. **Do not** leave `DOCS_ENABLED=true` on a public tool if you want a smaller attack surface.  
4. **Do not** raise `DAILY_ADMIN_LOG_MAX_PAGES` aggressively — use replicas for history instead.  

---

## Related docs

- [toolforge.md](toolforge.md) — reference detail  
- [DATA_COLLECTION.md](DATA_COLLECTION.md) — load budgets  
- [SECURITY.md](SECURITY.md) — security review  
- [PROJECT_CONFIGURATION.md](PROJECT_CONFIGURATION.md) — maintenance tracks  
