"""Maintenance backlog collection from configured categories."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health import BacklogSnapshot
from app.models.project import Project
from app.providers.base import SeriesPoint, SeriesResult
from app.providers.mediawiki import MediaWikiProvider
from app.services.registry import health_config_version
from app.pipeline.store import upsert_series
from app.timeutil import month_start, utc_today

logger = logging.getLogger(__name__)


async def _upsert_backlog(
    session: AsyncSession,
    row: dict[str, Any],
) -> None:
    dialect = session.bind.dialect.name if session.bind is not None else "sqlite"
    insert = sqlite_insert if dialect == "sqlite" else mysql_insert
    stmt = insert(BacklogSnapshot).values([row])
    if dialect == "sqlite":
        upsert = stmt.on_conflict_do_update(
            index_elements=["project_id", "track_id", "interval", "period_start"],
            set_={
                "open_count": stmt.excluded.open_count,
                "entered": stmt.excluded.entered,
                "left": stmt.excluded.left,
                "net": stmt.excluded.net,
                "source": stmt.excluded.source,
                "meta": stmt.excluded.meta,
                "config_version": stmt.excluded.config_version,
                "ingested_at": stmt.excluded.ingested_at,
            },
        )
    else:
        upsert = stmt.on_duplicate_key_update(
            open_count=stmt.inserted.open_count,
            entered=stmt.inserted.entered,
            left=stmt.inserted.left,
            net=stmt.inserted.net,
            source=stmt.inserted.source,
            meta=stmt.inserted.meta,
            config_version=stmt.inserted.config_version,
            ingested_at=stmt.inserted.ingested_at,
        )
    await session.execute(upsert)
    await session.commit()


async def collect_maintenance_backlogs(
    session: AsyncSession,
    project: Project,
    period: date | None = None,
    mw: MediaWikiProvider | None = None,
) -> dict[str, Any]:
    """
    Snapshot enabled maintenance category tracks for one UTC period (month start).
    """
    period = month_start(period or utc_today())
    health = project.health_config or {}
    cfg_ver = health_config_version(health)
    tracks = [t for t in (health.get("maintenance_tracks") or []) if t.get("enabled")]
    owns = mw is None
    if mw is None:
        mw = MediaWikiProvider()
        await mw.__aenter__()

    track_results: list[dict[str, Any]] = []
    total_open = 0.0
    try:
        for track in tracks:
            track_id = track["id"]
            kind = track.get("kind", "category")
            category = track.get("category")
            if kind != "category" or not category:
                track_results.append(
                    {
                        "track_id": track_id,
                        "status": "unavailable",
                        "reason": "category not configured or kind unsupported",
                    }
                )
                continue
            info = await mw.category_info(project.domain, category)
            if not info:
                track_results.append(
                    {
                        "track_id": track_id,
                        "status": "unavailable",
                        "reason": f"category not found: {category}",
                    }
                )
                continue
            open_count = float(info["pages"] + info.get("files", 0))
            # Net change vs previous snapshot if present
            prev = (
                await session.execute(
                    select(BacklogSnapshot)
                    .where(
                        BacklogSnapshot.project_id == project.id,
                        BacklogSnapshot.track_id == track_id,
                        BacklogSnapshot.interval == "month",
                        BacklogSnapshot.period_start < period,
                    )
                    .order_by(BacklogSnapshot.period_start.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            net = None if prev is None else open_count - float(prev.open_count)
            now = datetime.now(timezone.utc)
            await _upsert_backlog(
                session,
                {
                    "project_id": project.id,
                    "track_id": track_id,
                    "interval": "month",
                    "period_start": period,
                    "open_count": open_count,
                    "entered": None,
                    "left": None,
                    "net": net,
                    "source": "mediawiki",
                    "meta": {"category": category, "categoryinfo": info, "label": track.get("label")},
                    "config_version": cfg_ver,
                    "ingested_at": now,
                },
            )
            # Also store as metric_points for charting
            series = SeriesResult(
                metric_id=f"maintenance.track.{track_id}.open",
                points=[SeriesPoint(period_start=period, value=open_count)],
                source="mediawiki",
            )
            await upsert_series(session, project.id, series, "month")
            total_open += open_count
            track_results.append(
                {"track_id": track_id, "status": "ok", "open_count": open_count, "net": net}
            )

        if any(r.get("status") == "ok" for r in track_results):
            await upsert_series(
                session,
                project.id,
                SeriesResult(
                    metric_id="maintenance.open_total",
                    points=[SeriesPoint(period_start=period, value=total_open)],
                    source="mediawiki",
                ),
                "month",
            )
        return {
            "project_id": project.id,
            "period": period.isoformat(),
            "tracks": track_results,
            "open_total": total_open,
            "config_version": cfg_ver,
        }
    finally:
        if owns:
            await mw.__aexit__(None, None, None)
