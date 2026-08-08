"""Ingestion orchestration."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.ingestion import IngestionRun
from app.models.project import Project
from app.pipeline.store import upsert_page_snapshot, upsert_series
from app.providers.aqs import AQSProvider
from app.providers.mediawiki import MediaWikiProvider
from app.timeutil import month_start, months_back, utc_today

logger = logging.getLogger(__name__)


async def _start_run(
    session: AsyncSession, job_name: str, project_id: str | None
) -> IngestionRun:
    run = IngestionRun(job_name=job_name, project_id=project_id, status="running", checkpoint={}, stats={})
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def _finish_run(
    session: AsyncSession,
    run: IngestionRun,
    status: str,
    stats: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    run.status = status
    run.finished_at = datetime.now(timezone.utc)
    run.stats = stats or {}
    run.error = error
    await session.commit()


async def ingest_project_aqs(
    session: AsyncSession,
    project: Project,
    start: date | None = None,
    end: date | None = None,
    settings: Settings | None = None,
    aqs: AQSProvider | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    end = end or month_start(utc_today())
    start = start or months_back(end, settings.ingest_default_months)
    run = await _start_run(session, "aqs_monthly", project.id)
    owns = aqs is None
    if aqs is None:
        aqs = AQSProvider(settings)
        await aqs.__aenter__()
    points_written = 0
    metrics = 0
    try:
        series_list = await aqs.fetch_core_monthly(
            project.aqs_project, project.pageviews_project, start, end
        )
        for series in series_list:
            n = await upsert_series(session, project.id, series, "month")
            points_written += n
            metrics += 1

        # Latest complete month top pages (if available)
        top_month = end if end.day == 1 else month_start(end)
        # Use previous month for tops (current month may be incomplete)
        y, m = top_month.year, top_month.month
        if m == 1:
            y, m = y - 1, 12
        else:
            m -= 1
        try:
            top_edits = await aqs.fetch_top_pages_by_edits(project.aqs_project, y, m)
            await upsert_page_snapshot(
                session, project.id, "top_by_edits", "month", date(y, m, 1), top_edits
            )
            top_views = await aqs.fetch_top_pageviews(project.pageviews_project, y, m)
            await upsert_page_snapshot(
                session, project.id, "top_by_pageviews", "month", date(y, m, 1), top_views
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Top pages fetch failed for %s: %s", project.id, exc)

        stats = {
            "points_written": points_written,
            "series": metrics,
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
        await _finish_run(session, run, "success", stats=stats)
        return stats
    except Exception as exc:
        logger.exception("Ingest failed for %s", project.id)
        await _finish_run(session, run, "failed", error=str(exc))
        raise
    finally:
        if owns:
            await aqs.__aexit__(None, None, None)


async def ingest_project_mediawiki_logs(
    session: AsyncSession,
    project: Project,
    start: date | None = None,
    end: date | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    end = end or utc_today()
    start = start or months_back(end, 6)
    run = await _start_run(session, "mediawiki_logs", project.id)
    points = 0
    async with MediaWikiProvider(settings) as mw:
        try:
            for log_type, metric_id in (("delete", "content.pages_deleted"), ("block", "moderation.blocks")):
                series = await mw.aggregate_logevents(
                    project.domain, log_type, start, end, metric_id, interval="month"
                )
                points += await upsert_series(session, project.id, series, "month")
            stats = {"points_written": points, "start": start.isoformat(), "end": end.isoformat()}
            await _finish_run(session, run, "success", stats=stats)
            return stats
        except Exception as exc:
            await _finish_run(session, run, "failed", error=str(exc))
            raise


async def ingest_all_enabled(
    session: AsyncSession,
    start: date | None = None,
    end: date | None = None,
    project_ids: list[str] | None = None,
    include_mediawiki: bool = False,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    q = select(Project).where(Project.enabled.is_(True)).order_by(Project.sort_order)
    if project_ids:
        q = q.where(Project.id.in_(project_ids))
    projects = list((await session.execute(q)).scalars().all())
    results: dict[str, Any] = {}
    async with AQSProvider(settings) as aqs:
        for project in projects:
            logger.info("Ingesting AQS for %s", project.id)
            results[project.id] = await ingest_project_aqs(
                session, project, start=start, end=end, settings=settings, aqs=aqs
            )
            if include_mediawiki:
                try:
                    results[f"{project.id}:mw"] = await ingest_project_mediawiki_logs(
                        session, project, start=start, end=end, settings=settings
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("MW logs failed for %s: %s", project.id, exc)
    return results
