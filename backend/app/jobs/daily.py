"""Daily Toolforge collection with hard budgets to protect shared infrastructure."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.collectors.admin_logs import collect_admin_logs
from app.collectors.maintenance import collect_maintenance_backlogs
from app.collectors.processes import collect_process_tracks
from app.models.project import Project
from app.pipeline.store import upsert_series
from app.providers.aqs import AQSProvider
from app.providers.mediawiki import MediaWikiProvider
from app.providers.replicas import ReplicasUnavailable, WikiReplicasProvider
from app.services.ingest import ingest_project_aqs
from app.services.registry import seed_metrics, seed_projects
from app.services.signals import compute_derived_metrics
from app.timeutil import month_start, months_back, utc_today

logger = logging.getLogger(__name__)


async def run_daily(
    session: AsyncSession,
    settings: Settings | None = None,
    project_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Incremental daily update designed for Toolforge:

    - Reload YAML registry (cheap, local)
    - AQS lookback limited to a few months (not full history)
    - Maintenance/process categoryinfo (few API calls per project)
    - Admin logs only for a short recent window with low page caps
    - Optional replica aggregates with lag gate + statement timeout
    - Pause between projects
    - Cap number of projects per run
    """
    settings = settings or get_settings()
    await seed_projects(session, settings)
    await seed_metrics(session, settings)
    session.expire_all()

    q = select(Project).where(Project.enabled.is_(True)).order_by(Project.sort_order, Project.id)
    projects = list((await session.execute(q)).scalars().all())
    if project_ids:
        wanted = set(project_ids)
        projects = [p for p in projects if p.id in wanted]
    projects = projects[: max(1, settings.daily_max_projects)]

    end = utc_today()
    aqs_start = months_back(month_start(end), settings.daily_aqs_lookback_months)
    log_start = end - timedelta(days=settings.daily_admin_log_days)

    summary: dict[str, Any] = {
        "projects": [],
        "aqs_start": aqs_start.isoformat(),
        "log_start": log_start.isoformat(),
        "settings": {
            "daily_max_projects": settings.daily_max_projects,
            "daily_aqs_lookback_months": settings.daily_aqs_lookback_months,
            "daily_admin_log_days": settings.daily_admin_log_days,
            "daily_admin_log_max_pages": settings.daily_admin_log_max_pages,
            "daily_use_replicas": settings.daily_use_replicas and settings.wiki_replicas_enabled,
            "http_min_interval_seconds": settings.http_min_interval_seconds,
        },
    }

    async with AQSProvider(settings) as aqs:
        for i, project in enumerate(projects):
            entry: dict[str, Any] = {"id": project.id, "steps": {}}
            logger.info("Daily job: project %s (%s/%s)", project.id, i + 1, len(projects))
            try:
                entry["steps"]["aqs"] = await ingest_project_aqs(
                    session,
                    project,
                    start=aqs_start,
                    end=month_start(end),
                    settings=settings,
                    aqs=aqs,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("AQS daily failed for %s", project.id)
                entry["steps"]["aqs"] = {"error": str(exc)}

            try:
                async with MediaWikiProvider(settings) as mw:
                    entry["steps"]["maintenance"] = await collect_maintenance_backlogs(
                        session, project, mw=mw
                    )
                    entry["steps"]["processes"] = await collect_process_tracks(
                        session, project, mw=mw
                    )
                    if settings.daily_use_mediawiki_logs:
                        entry["steps"]["admin_logs"] = await collect_admin_logs(
                            session,
                            project,
                            start=log_start,
                            end=end,
                            mw=mw,
                            max_pages=settings.daily_admin_log_max_pages,
                        )
            except Exception as exc:  # noqa: BLE001
                logger.exception("MW daily failed for %s", project.id)
                entry["steps"]["mediawiki"] = {"error": str(exc)}

            if settings.daily_use_replicas and settings.wiki_replicas_enabled and project.dbname:
                try:
                    async with WikiReplicasProvider(settings) as replicas:
                        if replicas.available:
                            rev = await replicas.fetch_reverts_monthly(
                                project.dbname, aqs_start, end
                            )
                            n = await upsert_series(session, project.id, rev, "month")
                            entry["steps"]["reverts_replica"] = {"points": n}
                            groups = (project.health_config or {}).get("admin_groups") or ["sysop"]
                            admins = await replicas.fetch_active_admins_monthly(
                                project.dbname, aqs_start, end, admin_groups=groups
                            )
                            n2 = await upsert_series(session, project.id, admins, "month")
                            entry["steps"]["active_admins_replica"] = {"points": n2}
                except ReplicasUnavailable as exc:
                    entry["steps"]["replicas"] = {"skipped": str(exc)}
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Replica daily failed for %s", project.id)
                    entry["steps"]["replicas"] = {"error": str(exc)}

            try:
                entry["steps"]["derived"] = await compute_derived_metrics(session, project)
            except Exception as exc:  # noqa: BLE001
                entry["steps"]["derived"] = {"error": str(exc)}

            summary["projects"].append(entry)
            if i + 1 < len(projects) and settings.daily_project_pause_seconds > 0:
                await asyncio.sleep(settings.daily_project_pause_seconds)

    return summary
