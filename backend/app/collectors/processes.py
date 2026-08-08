"""Community process / governance queue snapshots."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health import ProcessSnapshot
from app.models.project import Project
from app.providers.mediawiki import MediaWikiProvider
from app.services.registry import health_config_version
from app.timeutil import month_start, utc_today

logger = logging.getLogger(__name__)


async def collect_process_tracks(
    session: AsyncSession,
    project: Project,
    period: date | None = None,
    mw: MediaWikiProvider | None = None,
) -> dict[str, Any]:
    period = month_start(period or utc_today())
    health = project.health_config or {}
    cfg_ver = health_config_version(health)
    tracks = [t for t in (health.get("process_tracks") or []) if t.get("enabled")]
    owns = mw is None
    if mw is None:
        mw = MediaWikiProvider()
        await mw.__aenter__()

    results = []
    try:
        dialect = session.bind.dialect.name if session.bind is not None else "sqlite"
        insert = sqlite_insert if dialect == "sqlite" else mysql_insert
        for track in tracks:
            track_id = track["id"]
            category = track.get("category")
            if track.get("kind", "category") != "category" or not category:
                results.append({"track_id": track_id, "status": "unavailable", "reason": "not configured"})
                continue
            info = await mw.category_info(project.domain, category)
            if not info:
                results.append({"track_id": track_id, "status": "unavailable", "reason": "category missing"})
                continue
            open_count = float(info["pages"])
            now = datetime.now(timezone.utc)
            row = {
                "project_id": project.id,
                "track_id": track_id,
                "interval": "month",
                "period_start": period,
                "open_count": open_count,
                "opened": None,
                "closed": None,
                "median_days": None,
                "source": "mediawiki",
                "meta": {"category": category, "label": track.get("label"), "categoryinfo": info},
                "config_version": cfg_ver,
                "ingested_at": now,
            }
            stmt = insert(ProcessSnapshot).values([row])
            if dialect == "sqlite":
                upsert = stmt.on_conflict_do_update(
                    index_elements=["project_id", "track_id", "interval", "period_start"],
                    set_={
                        "open_count": stmt.excluded.open_count,
                        "meta": stmt.excluded.meta,
                        "config_version": stmt.excluded.config_version,
                        "ingested_at": stmt.excluded.ingested_at,
                    },
                )
            else:
                upsert = stmt.on_duplicate_key_update(
                    open_count=stmt.inserted.open_count,
                    meta=stmt.inserted.meta,
                    config_version=stmt.inserted.config_version,
                    ingested_at=stmt.inserted.ingested_at,
                )
            await session.execute(upsert)
            await session.commit()
            results.append({"track_id": track_id, "status": "ok", "open_count": open_count})
        return {"project_id": project.id, "period": period.isoformat(), "tracks": results}
    finally:
        if owns:
            await mw.__aexit__(None, None, None)
