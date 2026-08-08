# Boundary with Wikistats

## What Wikistats does

Wikimedia Wikistats / Wikimedia Analytics provide **authoritative high-level activity statistics**: edits, editors, pageviews, new pages, and related official aggregates.

## What WikiSignals does

WikiSignals analyzes **operational and community pressures**:

- maintenance backlog (configured queues)
- administrative workload
- governance / process queues
- conflict signals (reverts)
- bot dependency
- capacity ratios (workload per active editor, etc.)

## Integration rule

Do **not** independently reproduce a metric already authoritatively provided by Wikimedia Analytics or Wikistats unless there is a specific technical reason.

Prefer consuming official metrics while preserving:

- metric ID
- source
- source endpoint/dataset
- definition
- retrieved timestamp
- project and period

Spend local computation on metrics Wikistats does **not** provide.

## UI consequence

Official activity series appear under **Official context** and as **denominators** for health ratios — not as the primary dashboard surface.
