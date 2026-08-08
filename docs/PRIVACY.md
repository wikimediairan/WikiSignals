# Privacy & ethics

WikiSignals analyzes **public** contribution and readership statistics to help communities understand project health and capacity. It must not become a volunteer-surveillance platform.

## Principles

1. **Aggregate-first.** Primary dashboards and APIs expose aggregates (counts, rates, distributions), not individual behavioral timelines.
2. **No volunteer scoreboards.** Do not rank or score individual editors. AQS endpoints that list top *editors* are intentionally **not** wired into the Observatory UI.
3. **Pages, not people.** High-activity lists show pages (by edits or pageviews).
4. **No protected-attribute inference.** Never infer gender, ethnicity, politics, location of individuals, or other sensitive characteristics.
5. **Conflict signals carefully.** Revert metrics are community-health analytics. Never label users as “problematic.”
6. **Transparent methodology.** Every metric documents source, definition, and caveats.
7. **Responsible API use.** Requests to Wikimedia services use a descriptive User-Agent with contact information and respect rate limits.

## Data processed

- Public Wikimedia Analytics API aggregates
- Public MediaWiki API aggregates (e.g. log counts)
- Optional Toolforge wiki replica queries producing **aggregates** only for storage in Observatory tables

The Observatory stores project configuration, metric definitions, aggregate time series, optional page-title lists, cohort stage counts, and manual annotations.

## What we avoid

- Per-user leaderboards, “risk scores,” or watchlists of volunteers
- Cross-wiki identity graphs for individuals in the UI
- Demographic estimation models
- Publishing raw user-level extracts

## Contact

Configure `USER_AGENT` with a reachable contact for operators of each deployment.
