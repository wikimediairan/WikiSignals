"""Persist series points and snapshots."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric import MetricPoint, PageSnapshot
from app.providers.base import SeriesPoint, SeriesResult
from app.timeutil import Interval, period_start_for


def dimensions_hash(dimensions: dict[str, Any] | None) -> str:
    if not dimensions:
        return ""
    payload = json.dumps(dimensions, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


async def upsert_series(
    session: AsyncSession,
    project_id: str,
    series: SeriesResult,
    interval: str,
) -> int:
    """Upsert series points. Returns number of points written."""
    if not series.points:
        return 0
    dialect = session.bind.dialect.name if session.bind is not None else "sqlite"
    now = datetime.now(timezone.utc)
    rows = []
    for p in series.points:
        dims = p.dimensions or {}
        rows.append(
            {
                "project_id": project_id,
                "metric_id": series.metric_id,
                "interval": interval,
                "period_start": p.period_start,
                "value": float(p.value),
                "dimensions_hash": dimensions_hash(dims),
                "dimensions": dims,
                "source": series.source,
                "quality_flags": {},
                "ingested_at": now,
            }
        )

    written = 0
    chunk_size = 200
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        if dialect == "sqlite":
            stmt = sqlite_insert(MetricPoint).values(chunk)
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=[
                    "project_id",
                    "metric_id",
                    "interval",
                    "period_start",
                    "dimensions_hash",
                ],
                set_={
                    "value": stmt.excluded.value,
                    "source": stmt.excluded.source,
                    "dimensions": stmt.excluded.dimensions,
                    "quality_flags": stmt.excluded.quality_flags,
                    "ingested_at": stmt.excluded.ingested_at,
                },
            )
        else:
            stmt = mysql_insert(MetricPoint).values(chunk)
            upsert_stmt = stmt.on_duplicate_key_update(
                value=stmt.inserted.value,
                source=stmt.inserted.source,
                dimensions=stmt.inserted.dimensions,
                quality_flags=stmt.inserted.quality_flags,
                ingested_at=stmt.inserted.ingested_at,
            )
        await session.execute(upsert_stmt)
        written += len(chunk)
    await session.commit()
    return written


async def upsert_page_snapshot(
    session: AsyncSession,
    project_id: str,
    snapshot_type: str,
    interval: str,
    period_start: date,
    payload: list[dict[str, Any]],
    source: str = "aqs",
) -> None:
    dialect = session.bind.dialect.name if session.bind is not None else "sqlite"
    now = datetime.now(timezone.utc)
    row = {
        "project_id": project_id,
        "snapshot_type": snapshot_type,
        "interval": interval,
        "period_start": period_start,
        "payload": payload,
        "source": source,
        "ingested_at": now,
    }
    if dialect == "sqlite":
        stmt = sqlite_insert(PageSnapshot).values([row])
        upsert = stmt.on_conflict_do_update(
            index_elements=["project_id", "snapshot_type", "interval", "period_start"],
            set_={
                "payload": stmt.excluded.payload,
                "source": stmt.excluded.source,
                "ingested_at": stmt.excluded.ingested_at,
            },
        )
    else:
        stmt = mysql_insert(PageSnapshot).values([row])
        upsert = stmt.on_duplicate_key_update(
            payload=stmt.inserted.payload,
            source=stmt.inserted.source,
            ingested_at=stmt.inserted.ingested_at,
        )
    await session.execute(upsert)
    await session.commit()


async def rollup_from_daily(
    session: AsyncSession,
    project_id: str,
    metric_id: str,
    start: date,
    end: date,
    target_interval: Interval,
) -> int:
    """Sum daily points into week/month/quarter/year aggregates."""
    if target_interval == "day":
        return 0
    result = await session.execute(
        select(MetricPoint).where(
            MetricPoint.project_id == project_id,
            MetricPoint.metric_id == metric_id,
            MetricPoint.interval == "day",
            MetricPoint.period_start >= start,
            MetricPoint.period_start <= end,
            MetricPoint.dimensions_hash == "",
        )
    )
    daily = list(result.scalars().all())
    buckets: dict[date, float] = {}
    for pt in daily:
        key = period_start_for(pt.period_start, target_interval)
        buckets[key] = buckets.get(key, 0.0) + float(pt.value)

    series = SeriesResult(
        metric_id=metric_id,
        points=[SeriesPoint(period_start=k, value=v) for k, v in sorted(buckets.items())],
        source="rollup",
    )
    return await upsert_series(session, project_id, series, target_interval)
