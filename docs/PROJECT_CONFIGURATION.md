# Project health configuration

Each project YAML under `config/projects/` may include a `health:` block.

## Fields

| Field | Purpose |
|-------|---------|
| `admin_groups` | Groups considered administrators for capacity definitions |
| `bot_groups` | Bot groups (documentation; AQS bot types used for edit share) |
| `maintenance_tracks` | List of backlog queues (`id`, `kind`, `category`, `label`, `enabled`) |
| `process_tracks` | Governance/process queues |
| `protection.enabled` | Collect protect log aggregates |
| `reverts` | Revert analysis flags/methods |
| `signal_thresholds` | Transparent MoM rules for improving/stable/needs_attention |
| `new_editor_health.url` | Link to New Editor Health Dashboard |

## Enabling a maintenance track

1. Verify the category exists on the live wiki (`categoryinfo` via Action API).
2. Set `category` to the local title (namespace prefix optional; collector tries bare title and `Category:…`).
3. Set `enabled: true`.
4. Run:
   ```bash
   python -m app.jobs.cli collect-health --project fa.wikipedia
   ```
   This **reloads YAML into the database by default** (`--reload-config`), then snapshots category sizes.

**Important:** The API reads `health_config` from the **database**, not the YAML file on every request. Editing YAML alone does not change the UI until you re-seed/reload (or run `collect-health`, which reloads for you).

Check what the DB has:

```bash
curl -s http://127.0.0.1:8000/api/v1/projects/fa.wikipedia/backlogs | python3 -m json.tool
```

## Persian Wikipedia

`fa.wikipedia` ships with **placeholder tracks** (`enabled: false`, `category: null`) so no invented category names enter production. Community administrators should populate verified local maintenance and process categories.

## Do not

- Hard-code Persian category strings into Python collectors
- Assume every wiki shares English Wikipedia category names
- Infer causal events automatically on charts
