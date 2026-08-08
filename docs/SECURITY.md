# Security review — WikiSignals

**Scope:** Application code, Toolforge deployment posture, data handling.  
**Date:** 2026-08-08 (repo review).  
**App type:** Public **read-only** analytics; no end-user login in v1.

---

## 1. Executive summary

| Area | Rating | Notes |
|------|--------|-------|
| AuthN / AuthZ | N/A → acceptable | Public aggregates; no admin UI; no sessions |
| Injection (SQL) | Strong | SQLAlchemy ORM / parameterized; replica dbname validated |
| Injection (HTTP) | Strong | IDs validated; no shell exec |
| Secrets | Good if followed | Envvars only; never log passwords |
| XSS | Moderate–Good | Vue escapes; CSP headers added; ECharts/static only |
| CSRF | Low risk | No cookie sessions; CORS credentials off |
| SSRF | Low | Outbound URLs fixed to Wikimedia hosts in providers |
| Dependency / supply chain | Moderate | Pin/update regularly; no known mandatory CVE scan in CI yet |
| Privacy / ethics | Strong by design | Aggregate-first; no user scoreboards |
| Toolforge multi-tenant | Good with budgets | Daily caps, replica timeouts, lag gate |

**Verdict:** Suitable for **public Toolforge pilot** if production env settings below are applied. Not a high-risk app (no PII login, no writes from the internet), but **misconfigured User-Agent, open CORS, or heavy jobs** can still cause operational/security incidents.

---

## 2. Attack surface map

| Surface | Exposure | Risk |
|---------|----------|------|
| `GET /api/v1/*` | Public | Information disclosure of public aggregates (intended) |
| `GET /health` | Public | Low (status only) |
| `GET /docs` | Optional | Disable in production |
| SPA static | Public | XSS if third-party scripts injected (mitigated by CSP) |
| Outbound AQS/MW/replicas | Tool → WMF | Rate-limit / ToS if abusive |
| ToolsDB | Private network | Credential leak if envvars exposed |
| CLI jobs | Operator only | Safe if no untrusted input |

There is **no** public write API for annotations, metrics, or config in the current design.

---

## 3. Findings

### 3.1 High (must fix / must configure in prod)

| ID | Finding | Status |
|----|---------|--------|
| H1 | Fake/generic `USER_AGENT` causes blocks and may look like abusive clients | Documented + validation warnings; operators must set real contact |
| H2 | OpenAPI `/docs` exposes internal schema | **Fixed:** `DOCS_ENABLED=false` disables docs/openapi in production |
| H3 | CORS was wide open in spirit if mis-set to `*` | **Hardened:** methods limited to GET/HEAD/OPTIONS; credentials off; require explicit origins |

### 3.2 Medium

| ID | Finding | Status / mitigation |
|----|---------|---------------------|
| M1 | Export endpoint could be abused for large responses | **Fixed:** max projects/metrics, max 10-year range |
| M2 | SPA catch-all could confuse path handling | **Fixed:** reject `..` and `api/` prefixes |
| M3 | Admin log collection can be heavy (DoS against self / API) | **Fixed:** daily budgets + max_pages |
| M4 | Replica SQL if ever string-built unsafely | **Hardened:** dbname regex whitelist; bound parameters for values |
| M5 | No automated dependency CVE CI | **Open:** add Dependabot/renovate + `pip-audit` in CI |
| M6 | Security headers were missing | **Fixed:** CSP, nosniff, frame deny, referrer policy |

### 3.3 Low

| ID | Finding | Mitigation |
|----|---------|------------|
| L1 | Error messages may include upstream body snippets | Truncated; useful for UA debugging |
| L2 | Public metric values are cacheable | Short TTL (`PUBLIC_CACHE_MAX_AGE_SECONDS`, default 60) + `stale-while-revalidate`; SPA `index.html` is `no-cache` |
| L3 | Fonts loaded from Google Fonts | CSP allows fonts.googleapis.com; optional self-host later |
| L4 | SQLite local DB file permissions | Dev only; ToolsDB in production |

### 3.4 Privacy / ethics (product security)

| ID | Finding | Status |
|----|---------|--------|
| P1 | Individual editor surveillance | Not implemented; methodology forbids |
| P2 | Admin leaderboards | Not implemented; aggregates only |
| P3 | Cohort funnel | Soft-deprecated; no public user lists |
| P4 | Logevents contain targets | Only **counts** stored, not targets |

---

## 4. Code review notes

### Safe patterns observed

- SQLAlchemy ORM for ToolsDB; upserts via dialect insert APIs  
- Export and metrics use bound query parameters through ORM  
- No `eval`, `pickle`, `subprocess`, or shell=True in app code  
- Outbound HTTP only via shared client with UA + rate limit  
- Project/metric ID regex validation on key endpoints  

### Residual risks

- **Replica schema name** cannot be parameterized in MySQL; mitigation is strict `is_safe_dbname()` before formatting `` `{schema}` ``  
- **Shared Toolforge Redis** (if used later) must use unique `REDIS_KEY_PREFIX`  
- **Image supply chain**: use Toolforge buildservice from your git; review third-party npm/pypi updates  

---

## 5. Production configuration checklist

```bash
ENVIRONMENT=production
DOCS_ENABLED=false
CORS_ORIGINS=https://YOURTOOL.toolforge.org
USER_AGENT=WikiSignals/0.1 (https://github.com/wikimediairan/WikiSignals; you@real-email)
DATABASE_URL=mysql+aiomysql://…@tools.db.svc.wikimedia.cloud:3306/sXXXXX__wikisignals
# Never enable debug or SQL echo
LOG_LEVEL=INFO
```

Optional:

```bash
# If Redis is ever added
REDIS_KEY_PREFIX=wikisignals-YOURTOOL:
```

---

## 6. Secrets handling

| Secret | Store | Do not |
|--------|-------|--------|
| ToolsDB password | `toolforge envvars` | Git, screenshots, job logs |
| Replica password | `toolforge envvars` or file mode 600 | Echo in scripts |
| OAuth (future) | envvars + encryption at rest | Local `.env` on shared machines |

Rotate credentials if leaked via git history.

---

## 7. Recommended security tests (CI)

- Unit: `is_safe_project_id` / `is_safe_dbname` reject `';`, `../`, spaces  
- Integration: export rejects oversized ranges  
- Headers: response includes `X-Content-Type-Options`  
- `pip-audit` / `npm audit` on schedule  

---

## 8. Incident response (Toolforge)

1. Disable daily job: `toolforge jobs delete wikisignals-daily`  
2. If abusive outbound traffic: set `HTTP_MIN_INTERVAL_SECONDS=5`, `DAILY_MAX_PROJECTS=1`  
3. Rotate ToolsDB/replica passwords  
4. Check job logs for unexpected hosts (should only be Wikimedia)  

---

## 9. Summary for Toolforge admins

This tool:

- Serves **public aggregate** statistics  
- Performs **bounded** daily reads against AQS, Action API, and optional analytics replicas  
- Does **not** accept untrusted write payloads from the internet  
- Implements **statement timeouts** and **lag gates** on replicas  

It should be treated as a normal analytics tool, not a high-risk data processor — provided daily budgets stay in place.

---

## 10. Related

- Fresh deploy: [DEPLOY.md](DEPLOY.md)  
- Load budgets: [DATA_COLLECTION.md](DATA_COLLECTION.md)  
