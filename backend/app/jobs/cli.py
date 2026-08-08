"""WikiSignals CLI: bootstrap, ingest, health collectors, daily jobs."""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Optional

import typer
from sqlalchemy import select

from app.config import get_settings
from app.db import session as db_session
from app.db.session import init_engine
from app.models.project import Project
from app.providers.aqs import AQSProvider
from app.services.ingest import ingest_all_enabled
from app.services.metrics import get_metric_definition, query_series
from app.services.registry import bootstrap_registry
from app.timeutil import month_start, months_back, parse_date, utc_today

app = typer.Typer(help="WikiSignals jobs (community health analytics)", no_args_is_help=True)
logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))


def _session_factory():
    init_engine()
    factory = db_session.async_session_factory
    assert factory is not None
    return factory


async def _async_bootstrap(skip_ingest: bool, project: Optional[str], months: int) -> None:
    settings = get_settings()
    typer.echo(f"config_dir={settings.resolved_config_dir}")
    typer.echo(f"database_url_host={_safe_db_host(settings.database_url)}")
    factory = _session_factory()
    async with factory() as session:
        counts = await bootstrap_registry(session)
        typer.echo(f"Registry seeded: {counts}")
        if int(counts.get("projects") or 0) < 1:
            typer.echo(
                "ERROR: seeded 0 projects. Check config/projects on the image "
                "(unset CONFIG_DIR if it points at a missing path like /config).",
                err=True,
            )
            raise typer.Exit(1)
        if skip_ingest:
            return
        end = month_start(utc_today())
        start = months_back(end, months)
        ids = [project] if project else None
        # Default bootstrap focuses on Persian suite + peers if --all not limited
        if ids is None:
            preferred = [
                settings.default_project_id,
                "fa.wiktionary",
                "fa.wikisource",
                "fa.wikivoyage",
            ]
            results = await ingest_all_enabled(
                session, start=start, end=end, project_ids=preferred, include_mediawiki=False
            )
        else:
            results = await ingest_all_enabled(
                session, start=start, end=end, project_ids=ids, include_mediawiki=False
            )
        typer.echo(f"Ingest complete: {results}")


def _safe_db_host(url: str) -> str:
    """Log host/db without password."""
    try:
        # mysql+aiomysql://user:pass@host:3306/db
        after_at = url.split("@", 1)[1]
        return after_at
    except Exception:  # noqa: BLE001
        return "(unparseable)"


@app.command()
def bootstrap(
    skip_ingest: bool = typer.Option(False, help="Only seed registry, do not fetch AQS"),
    project: Optional[str] = typer.Option(None, help="Limit ingest to one project id"),
    months: int = typer.Option(24, help="Months of monthly AQS history to fetch"),
) -> None:
    """Seed project/metric registry and optionally pull public AQS data."""
    _setup_logging()
    asyncio.run(_async_bootstrap(skip_ingest, project, months))


async def _async_ingest(
    project: Optional[str],
    since: Optional[str],
    until: Optional[str],
    all_projects: bool,
    mediawiki: bool,
) -> None:
    factory = _session_factory()
    start = parse_date(since) if since else None
    end = parse_date(until) if until else None
    async with factory() as session:
        if project:
            results = await ingest_all_enabled(
                session,
                start=start,
                end=end,
                project_ids=[project],
                include_mediawiki=mediawiki,
            )
        else:
            results = await ingest_all_enabled(
                session,
                start=start,
                end=end,
                project_ids=None if all_projects else None,
                include_mediawiki=mediawiki,
            )
        typer.echo(results)


@app.command()
def ingest(
    project: Optional[str] = typer.Option(None, help="Project id, e.g. fa.wikipedia"),
    since: Optional[str] = typer.Option(None, help="Start date YYYY-MM-DD"),
    until: Optional[str] = typer.Option(None, help="End date YYYY-MM-DD"),
    all_projects: bool = typer.Option(False, "--all", help="Ingest all enabled projects"),
    mediawiki: bool = typer.Option(False, help="Also fetch experimental MW log aggregates"),
) -> None:
    """Incrementally ingest metrics from AQS (and optionally MediaWiki logs)."""
    _setup_logging()
    if not project and not all_projects:
        # default to default project
        project = get_settings().default_project_id
    asyncio.run(_async_ingest(project, since, until, all_projects, mediawiki))


async def _async_verify(project: str, metric: str, month: str) -> int:
    factory = _session_factory()
    period = month_start(parse_date(month if len(month) > 7 else f"{month}-01"))
    settings = get_settings()
    async with factory() as session:
        proj = await session.get(Project, project)
        if not proj:
            typer.echo(f"Project not found: {project}", err=True)
            return 1
        definition = await get_metric_definition(session, metric)
        stored = await query_series(session, project, metric, period, period, "month")
        stored_val = stored[0].value if stored else None

        live_val = None
        async with AQSProvider(settings) as aqs:
            if metric == "editors.active":
                # recompute live
                from app.providers.aqs import ACTIVITY_LEVELS, _sum_series

                parts = []
                for level, mid in ACTIVITY_LEVELS.items():
                    if mid in (
                        "editors.activity_5_24",
                        "editors.activity_25_99",
                        "editors.highly_active",
                    ):
                        parts.append(
                            await aqs.fetch_editors(
                                proj.aqs_project,
                                period,
                                period,
                                activity_level=level,
                                metric_id=mid,
                            )
                        )
                live_series = _sum_series("editors.active", parts)
                match = [p for p in live_series.points if p.period_start == period]
                live_val = match[0].value if match else None
            elif metric.startswith("edits."):
                from app.providers.aqs import EDITOR_TYPES_EDITS

                inv = {v: k for k, v in EDITOR_TYPES_EDITS.items()}
                et = inv.get(metric, "all-editor-types")
                series = await aqs.fetch_edits(
                    proj.aqs_project, period, period, editor_type=et, metric_id=metric
                )
                match = [p for p in series.points if p.period_start == period]
                live_val = match[0].value if match else None
            elif metric == "readers.pageviews":
                series = await aqs.fetch_pageviews(proj.pageviews_project, period, period)
                match = [p for p in series.points if p.period_start == period]
                live_val = match[0].value if match else None
            elif metric == "editors.new_accounts":
                series = await aqs.fetch_new_registered_users(proj.aqs_project, period, period)
                match = [p for p in series.points if p.period_start == period]
                live_val = match[0].value if match else None
            else:
                typer.echo(f"Live verify not implemented for metric {metric}", err=True)
                return 2

        typer.echo(f"project={project} metric={metric} month={period.isoformat()}")
        typer.echo(f"stored={stored_val} live_aqs={live_val}")
        if definition:
            typer.echo(f"definition={definition.definition[:120]}...")
        if stored_val is None:
            typer.echo("FAIL: no stored value", err=True)
            return 1
        if live_val is None:
            typer.echo("FAIL: no live AQS value", err=True)
            return 1
        if float(stored_val) != float(live_val):
            typer.echo("FAIL: mismatch", err=True)
            return 1
        typer.echo("OK: stored matches live AQS")
        return 0


@app.command()
def verify(
    project: str = typer.Option("fa.wikipedia"),
    metric: str = typer.Option("editors.active"),
    month: str = typer.Option(..., help="YYYY-MM or YYYY-MM-DD"),
) -> None:
    """Compare a stored aggregate to a live AQS fetch (exact match expected for AQS metrics)."""
    _setup_logging()
    code = asyncio.run(_async_verify(project, metric, month))
    raise typer.Exit(code)


async def _async_seed_only() -> None:
    settings = get_settings()
    typer.echo(f"config_dir={settings.resolved_config_dir}")
    typer.echo(f"database_url_host={_safe_db_host(settings.database_url)}")
    factory = _session_factory()
    async with factory() as session:
        counts = await bootstrap_registry(session)
        typer.echo(f"Registry seeded: {counts}")
        if int(counts.get("projects") or 0) < 1:
            typer.echo(
                "ERROR: seeded 0 projects. Unset CONFIG_DIR if set to /config "
                f"(resolved={settings.resolved_config_dir}).",
                err=True,
            )
            raise typer.Exit(1)


@app.command("seed-registry")
def seed_registry_only() -> None:
    """Seed projects/metrics/annotations without network calls."""
    _setup_logging()
    asyncio.run(_async_seed_only())


@app.command("diagnose")
def diagnose() -> None:
    """Print config/DB resolution (no secrets) for Toolforge debugging."""
    _setup_logging()
    settings = get_settings()
    cfg = settings.resolved_config_dir
    projects = list((cfg / "projects").glob("*.yaml")) if (cfg / "projects").is_dir() else []
    typer.echo(f"app_name={settings.app_name}")
    typer.echo(f"environment={settings.environment}")
    typer.echo(f"config_dir_env={settings.config_dir!r}")
    typer.echo(f"resolved_config_dir={cfg}")
    typer.echo(f"project_yaml_count={len(projects)}")
    typer.echo(f"project_yaml_sample={[p.name for p in projects[:5]]}")
    typer.echo(f"database_url_host={_safe_db_host(settings.database_url)}")
    typer.echo(f"tool_toolsdb_user_set={bool(settings.tool_toolsdb_user)}")
    typer.echo(f"user_agent={settings.user_agent!r}")
    # Replica config (conflict signals: reverts / active admins)
    typer.echo(f"wiki_replicas_enabled={settings.wiki_replicas_enabled}")
    typer.echo(f"wiki_replicas_host={settings.wiki_replicas_host!r}")
    typer.echo(f"wiki_replicas_port={settings.wiki_replicas_port}")
    typer.echo(f"wiki_replicas_user_set={bool(settings.wiki_replicas_user)}")
    typer.echo(f"wiki_replicas_password_set={bool(settings.wiki_replicas_password)}")
    typer.echo(f"tool_replica_user_set={bool(settings.tool_replica_user)}")
    typer.echo(f"daily_use_replicas={settings.daily_use_replicas}")
    replica_ready = bool(
        settings.wiki_replicas_enabled
        and settings.wiki_replicas_host
        and settings.wiki_replicas_user
    )
    typer.echo(f"wiki_replicas_ready={replica_ready}")
    if settings.wiki_replicas_enabled and not replica_ready:
        typer.echo(
            "HINT: set WIKI_REPLICAS_HOST + WIKI_REPLICAS_USER/PASSWORD "
            "(or TOOL_REPLICA_USER/PASSWORD from ~/replica.my.cnf), then run collect-replicas",
            err=True,
        )


async def _async_collect_health(project: str, months: int, reload_config: bool) -> None:
    from app.collectors.admin_logs import collect_admin_logs
    from app.collectors.maintenance import collect_maintenance_backlogs
    from app.collectors.processes import collect_process_tracks
    from app.providers.mediawiki import MediaWikiProvider
    from app.services.registry import seed_projects
    from app.services.signals import compute_derived_metrics

    factory = _session_factory()
    end = utc_today()
    start = months_back(end, months)
    async with factory() as session:
        if reload_config:
            n = await seed_projects(session)
            typer.echo(f"Reloaded project registry from YAML ({n} projects)")
            # Drop cached ORM state so health_config comes from the updated DB row
            session.expire_all()
        proj = await session.get(Project, project)
        if not proj:
            typer.echo(f"Project not found: {project}", err=True)
            raise typer.Exit(1)
        tracks = (proj.health_config or {}).get("maintenance_tracks") or []
        enabled = [t for t in tracks if t.get("enabled")]
        if enabled:
            detail = ", ".join(f"{t.get('id')}={t.get('category')!r}" for t in enabled)
            typer.echo(f"health_config: {len(enabled)} enabled maintenance track(s): {detail}")
        else:
            typer.echo(
                "health_config: no enabled maintenance tracks "
                "(edit config/projects/<id>.yaml and re-run collect-health)"
            )
        async with MediaWikiProvider() as mw:
            maint = await collect_maintenance_backlogs(session, proj, mw=mw)
            typer.echo(f"maintenance: {maint}")
            proc = await collect_process_tracks(session, proj, mw=mw)
            typer.echo(f"processes: {proc}")
            admin = await collect_admin_logs(session, proj, start=start, end=end, mw=mw)
            typer.echo(f"admin_logs: {admin}")
        derived = await compute_derived_metrics(session, proj)
        typer.echo(f"derived: {derived}")


@app.command("collect-health")
def collect_health(
    project: str = typer.Option(..., help="Project id, e.g. fa.wikipedia"),
    months: int = typer.Option(6, help="Months of admin log history to fetch"),
    reload_config: bool = typer.Option(
        True,
        "--reload-config/--no-reload-config",
        help="Reload project YAML (including health tracks) into the DB before collecting",
    ),
) -> None:
    """Collect maintenance backlogs, process queues, admin logs; compute derived signals.

    Does **not** collect reverts/conflict metrics — those need wiki replicas via collect-replicas
    or the daily job with WIKI_REPLICAS_ENABLED.

    By default reloads config/projects/*.yaml so YAML edits apply without a separate seed step.
    """
    _setup_logging()
    asyncio.run(_async_collect_health(project, months, reload_config))


async def _async_collect_replicas(project: str, months: int, chunk_months: int) -> None:
    """Backfill aggregate reverts + active admins from Toolforge wiki replicas."""
    from calendar import monthrange

    from app.pipeline.store import upsert_series
    from app.providers.replicas import ReplicasUnavailable, WikiReplicasProvider
    from app.services.signals import compute_derived_metrics
    from app.timeutil import add_interval, next_month_start

    settings = get_settings()
    if not settings.wiki_replicas_enabled:
        typer.echo(
            "ERROR: WIKI_REPLICAS_ENABLED is not true. "
            "Env vars alone do nothing until collect-replicas/daily runs.",
            err=True,
        )
        raise typer.Exit(1)
    if not settings.wiki_replicas_host:
        typer.echo("ERROR: WIKI_REPLICAS_HOST is empty", err=True)
        raise typer.Exit(1)
    if not settings.wiki_replicas_user:
        typer.echo(
            "ERROR: replica user empty. Set WIKI_REPLICAS_USER + WIKI_REPLICAS_PASSWORD "
            "from ~/replica.my.cnf (or TOOL_REPLICA_USER / TOOL_REPLICA_PASSWORD).",
            err=True,
        )
        raise typer.Exit(1)

    factory = _session_factory()
    end = utc_today()
    start = months_back(month_start(end), months)
    chunk = max(1, chunk_months)
    typer.echo(
        f"collect-replicas project={project} range={start}..{end} "
        f"chunk_months={chunk} host={settings.wiki_replicas_host}"
    )

    async with factory() as session:
        proj = await session.get(Project, project)
        if not proj:
            typer.echo(f"Project not found: {project}", err=True)
            raise typer.Exit(1)
        if not proj.dbname:
            typer.echo(f"Project {project} has no dbname for replicas", err=True)
            raise typer.Exit(1)

        total_rev = 0
        total_admins = 0
        try:
            async with WikiReplicasProvider(settings) as replicas:
                if not replicas.available:
                    typer.echo("ERROR: WikiReplicasProvider.available is false", err=True)
                    raise typer.Exit(1)
                lag = await replicas.check_lag_seconds()
                typer.echo(f"replica_lag_seconds={lag}")
                await replicas.ensure_lag_ok()

                # Chunk the range so max_statement_time is less likely to kill long history
                cursor = start
                while cursor <= end:
                    last_month_start = add_interval(cursor, "month", chunk - 1)
                    last_day = monthrange(last_month_start.year, last_month_start.month)[1]
                    chunk_end = min(end, last_month_start.replace(day=last_day))

                    typer.echo(f"  query reverts {cursor}..{chunk_end} dbname={proj.dbname}")
                    rev = await replicas.fetch_reverts_monthly(proj.dbname, cursor, chunk_end)
                    n = await upsert_series(session, proj.id, rev, "month")
                    total_rev += n
                    typer.echo(f"  reverts points upserted={n}")

                    groups = (proj.health_config or {}).get("admin_groups") or ["sysop"]
                    admins = await replicas.fetch_active_admins_monthly(
                        proj.dbname, cursor, chunk_end, admin_groups=groups
                    )
                    n2 = await upsert_series(session, proj.id, admins, "month")
                    total_admins += n2
                    typer.echo(f"  active_admins points upserted={n2}")

                    cursor = next_month_start(chunk_end)
        except ReplicasUnavailable as exc:
            typer.echo(f"ERROR: replicas unavailable: {exc}", err=True)
            raise typer.Exit(1) from exc
        except Exception as exc:  # noqa: BLE001
            logger.exception("collect-replicas failed")
            typer.echo(f"ERROR: {exc}", err=True)
            raise typer.Exit(1) from exc

        derived = await compute_derived_metrics(session, proj)
        typer.echo(
            f"done: reverts_points={total_rev} active_admins_points={total_admins} "
            f"derived={derived}"
        )


@app.command("collect-replicas")
def collect_replicas(
    project: str = typer.Option("fa.wikipedia", help="Project id, e.g. fa.wikipedia"),
    months: int = typer.Option(24, help="Months of monthly revert/admin history to fetch"),
    chunk_months: int = typer.Option(
        3,
        help="Fetch this many months per SQL query (keeps under max_statement_time)",
    ),
) -> None:
    """Backfill conflict metrics (reverts.count, active admins) from wiki replicas.

    Requires WIKI_REPLICAS_ENABLED, HOST, and USER/PASSWORD. Env vars alone do not
    populate the API — this job (or daily) must run successfully first.
    """
    _setup_logging()
    asyncio.run(_async_collect_replicas(project, months, chunk_months))


async def _async_compute_signals(project: str) -> None:
    from app.services.signals import build_health_signals, compute_derived_metrics

    factory = _session_factory()
    async with factory() as session:
        proj = await session.get(Project, project)
        if not proj:
            typer.echo(f"Project not found: {project}", err=True)
            raise typer.Exit(1)
        derived = await compute_derived_metrics(session, proj)
        signals = await build_health_signals(session, proj)
        typer.echo(f"derived: {derived}")
        typer.echo(f"signals: {len(signals.get('signals', []))} primary + {len(signals.get('context', []))} context")


@app.command("compute-signals")
def compute_signals(
    project: str = typer.Option(..., help="Project id"),
) -> None:
    """Recompute derived ratios and print health signal summary."""
    _setup_logging()
    asyncio.run(_async_compute_signals(project))


async def _async_check_connectivity() -> int:
    from app.providers.http_client import RateLimitedClient, validate_user_agent

    settings = get_settings()
    typer.echo(f"USER_AGENT={settings.user_agent!r}")
    warnings = validate_user_agent(settings.user_agent)
    for w in warnings:
        typer.echo(f"WARNING: {w}", err=True)
    if any("@localhost" in settings.user_agent.lower() for _ in [1]):
        typer.echo(
            "Fix: set USER_AGENT in .env to include a real email or https URL, then retry.",
            err=True,
        )

    urls = [
        (
            "AQS editors",
            "https://wikimedia.org/api/rest_v1/metrics/editors/aggregate/"
            "fa.wikipedia.org/user/all-page-types/5..24-edits/monthly/20260101/20260201",
        ),
        (
            "MediaWiki siteinfo",
            "https://fa.wikipedia.org/w/api.php?action=query&meta=siteinfo&siprop=general&format=json",
        ),
    ]
    ok = 0
    async with RateLimitedClient(settings) as client:
        for name, url in urls:
            try:
                data = await client.get_json(url)
                typer.echo(f"OK  {name}")
                if data is not None:
                    ok += 1
            except Exception as exc:  # noqa: BLE001
                typer.echo(f"FAIL {name}: {exc}", err=True)
    if ok == len(urls):
        typer.echo("Connectivity check passed.")
        return 0
    typer.echo("Connectivity check failed.", err=True)
    return 1


@app.command("check-connectivity")
def check_connectivity() -> None:
    """Probe Wikimedia AQS + MediaWiki API with the configured User-Agent."""
    _setup_logging()
    raise typer.Exit(asyncio.run(_async_check_connectivity()))


async def _async_daily(project: Optional[str]) -> None:
    from app.jobs.daily import run_daily

    factory = _session_factory()
    async with factory() as session:
        ids = [project] if project else None
        summary = await run_daily(session, project_ids=ids)
        typer.echo(summary)


@app.command("daily")
def daily(
    project: Optional[str] = typer.Option(
        None, help="Limit to one project (default: up to DAILY_MAX_PROJECTS enabled projects)"
    ),
) -> None:
    """Toolforge-friendly daily incremental collection (budgeted AQS/MW/replicas)."""
    _setup_logging()
    asyncio.run(_async_daily(project))


if __name__ == "__main__":
    app()
