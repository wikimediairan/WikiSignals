# Data collection load budgets

Goal: keep **daily** updates safe for Toolforge, Wikimedia APIs, and wiki replicas.

## Source priority

| Need | Preferred source | Avoid daily |
|------|------------------|-------------|
| Edits, editors, pageviews | **AQS** (official) | Re-scanning revision tables |
| Maintenance backlog size | **categoryinfo** API | Full categorymember dumps |
| Admin action volume | **Replicas** (aggregate) or **capped** logevents | Unlimited API walk |
| Revert counts | **Replicas** + `mw-reverted` tag | Per-user revision scans |
| Process queue size | categoryinfo / configured tracks | Scraping talk HTML |

## Daily job (`python -m app.jobs.cli daily`)

Configured via env (defaults in parentheses):

| Setting | Default | Meaning |
|---------|---------|---------|
| `DAILY_MAX_PROJECTS` | 8 | Cap projects per run |
| `DAILY_AQS_LOOKBACK_MONTHS` | 3 | AQS refresh window only |
| `DAILY_ADMIN_LOG_DAYS` | 35 | MW logevents recent window |
| `DAILY_ADMIN_LOG_MAX_PAGES` | 8 | Max continuations per log type |
| `DAILY_PROJECT_PAUSE_SECONDS` | 2 | Sleep between projects |
| `HTTP_MIN_INTERVAL_SECONDS` | 0.5–0.75 | Delay between HTTP calls |
| `WIKI_REPLICAS_MAX_STATEMENT_TIME` | 30 | Abort long replica SQL |
| `WIKI_REPLICAS_MAX_LAG_SECONDS` | 600 | Skip replicas if lag too high |

## Estimated daily load (single project, fa.wikipedia)

Rough order of magnitude:

- **AQS:** ~15–25 HTTP GETs (series for lookback months)  
- **categoryinfo:** 1 call per enabled maintenance/process track  
- **logevents:** up to 5 types × ≤8 pages × ≤500 rows (worst case) — keep pages low  
- **replicas:** 1–2 aggregate queries with time bounds  

This is far lighter than a full history rebuild or dump processing.

## Bootstrap (heavy, rare)

`bootstrap --months 24` and long `collect-health --months N` are for **initial fill** only. Do not schedule them daily.

## Scaling to more wikis

1. Stabilize one wiki.  
2. Enable a second with staggered schedule or low `DAILY_MAX_PROJECTS`.  
3. Move admin volume to replicas; set `DAILY_USE_MEDIAWIKI_LOGS=false` if API pressure rises.  
