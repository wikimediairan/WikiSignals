# Data collection budgets

Keep daily updates safe for Toolforge, Wikimedia APIs, and wiki replicas.

## Source priority

| Need | Preferred source | Avoid on a daily schedule |
|------|------------------|---------------------------|
| Edits, editors, pageviews | **AQS** (official) | Re-scanning revision tables |
| Maintenance backlog size | **categoryinfo** API | Full category member dumps |
| Admin action volume | **Replicas** (aggregate) or capped logevents | Unlimited API walks |
| Revert counts | **Replicas** + `mw-reverted` | Per-user revision scans |
| Process queue size | categoryinfo / configured tracks | Scraping HTML |

## Commands

| Command | When | Load |
|---------|------|------|
| `bootstrap` / `bootstrap-5y` / `ingest-5y` | **Once** (initial AQS history) | High |
| `collect-health` | Once / after YAML track changes | Medium (MW API) |
| `collect-replicas` | Once for backfill; then `daily` | Medium (SQL, chunked) |
| `daily` | **Scheduled** | Low (budgeted) |

## Daily job settings

| Env var | Default | Meaning |
|---------|---------|---------|
| `DAILY_MAX_PROJECTS` | 8 | Cap projects per run |
| `DAILY_AQS_LOOKBACK_MONTHS` | 3 | AQS refresh window only |
| `DAILY_ADMIN_LOG_DAYS` | 35 | MW logevents recent window |
| `DAILY_ADMIN_LOG_MAX_PAGES` | 8 | Max continuations per log type |
| `DAILY_PROJECT_PAUSE_SECONDS` | 2 | Sleep between projects |
| `DAILY_USE_MEDIAWIKI_LOGS` | true | Collect capped admin logs via API |
| `DAILY_USE_REPLICAS` | true | Run replica step when enabled |
| `HTTP_MIN_INTERVAL_SECONDS` | 0.5–0.75 | Delay between HTTP calls |
| `WIKI_REPLICAS_MAX_STATEMENT_TIME` | 30 | Abort long replica SQL |
| `WIKI_REPLICAS_MAX_LAG_SECONDS` | 600 | Skip replicas if lag too high |

## Rough daily load (one project)

- **AQS:** ~15–25 GETs for the lookback window  
- **categoryinfo:** 1 call per enabled maintenance/process track  
- **logevents:** up to a few types × ≤8 pages (keep pages low)  
- **replicas:** 1–2 aggregate queries with time bounds  

## Scaling to more wikis

1. Stabilize one wiki.  
2. Enable a second with low `DAILY_MAX_PROJECTS` or a staggered job.  
3. Prefer replicas for admin volume; set `DAILY_USE_MEDIAWIKI_LOGS=false` if API pressure rises.  

Deploy steps: [DEPLOY.md](DEPLOY.md).
