# Project health configuration

Each project YAML under `config/projects/` may include a `health:` block.

## Fields

| Field | Purpose |
|-------|---------|
| `admin_groups` | Groups treated as administrators for capacity definitions |
| `bot_groups` | Bot groups (documentation; AQS bot types used for edit share) |
| `maintenance_tracks` | Backlog queues (`id`, `kind`, `category`, `label`, `enabled`) |
| `process_tracks` | Governance / process queues |
| `protection.enabled` | Collect protect log aggregates |
| `reverts` | Revert analysis flags / preferred methods |
| `signal_thresholds` | Transparent MoM rules for improving / stable / needs_attention |
| `new_editor_health.url` | Link to New Editor Health Dashboard |

## Enabling a maintenance or process track

1. Verify the category exists on the live wiki (`categoryinfo` via Action API).  
2. Set `category` to the local title (with or without `Category:` prefix; the collector tries both).  
3. Set `enabled: true`.  
4. Reload and collect:

   ```bash
   python -m app.jobs.cli collect-health --project fa.wikipedia
   ```

   Default is `--reload-config` (YAML → DB), then category snapshots.

**Important:** The API reads `health_config` from the **database**, not the YAML file on every request. Editing YAML alone does not change the UI until you re-seed/reload (or run `collect-health`).

Check what the DB has:

```bash
curl -sS http://127.0.0.1:8000/api/v1/projects/fa.wikipedia/backlogs | python3 -m json.tool
```

## Reverts (conflict)

Reverts are **not** configured as category tracks. They require:

1. `WIKI_REPLICAS_*` env vars (Toolforge)  
2. `collect-replicas` or a successful replica step in `daily`  

See [DEPLOY.md](DEPLOY.md).

## Persian Wikipedia

`config/projects/fa.wikipedia.yaml` ships with sample maintenance/process categories used by the default workspace. Treat them as community-owned configuration: verify titles on the live wiki when you fork the tool for another community.

## Do not

- Hard-code Persian (or any language) category strings into Python collectors  
- Assume every wiki shares English Wikipedia category names  
- Infer causal events automatically on charts  

## Adding a new project

1. Copy an existing YAML under `config/projects/`.  
2. Set `id`, `domain`, `dbname`, `aqs_project`, language, and tracks.  
3. `seed-registry` or `collect-health` · then `bootstrap` / `daily`.  

Contribute workflow: [../CONTRIBUTING.md](../CONTRIBUTING.md).
