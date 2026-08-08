"""Read path for metric series and exports."""

from __future__ import annotations

import csv
import io
import json
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cohort import CohortPoint
from app.models.metric import MetricDefinition, MetricPoint, PageSnapshot
from app.models.project import Project
from app.timeutil import parse_date


async def get_project(session: AsyncSession, project_id: str) -> Project | None:
    return await session.get(Project, project_id)


async def list_projects(session: AsyncSession, enabled_only: bool = True) -> list[Project]:
    q = select(Project).order_by(Project.sort_order, Project.id)
    if enabled_only:
        q = q.where(Project.enabled.is_(True))
    return list((await session.execute(q)).scalars().all())


async def list_metric_definitions(session: AsyncSession) -> list[MetricDefinition]:
    q = select(MetricDefinition).order_by(MetricDefinition.sort_order, MetricDefinition.id)
    return list((await session.execute(q)).scalars().all())


async def get_metric_definition(session: AsyncSession, metric_id: str) -> MetricDefinition | None:
    return await session.get(MetricDefinition, metric_id)


async def query_series(
    session: AsyncSession,
    project_id: str,
    metric_id: str,
    start: date,
    end: date,
    interval: str = "month",
) -> list[MetricPoint]:
    q = (
        select(MetricPoint)
        .where(
            MetricPoint.project_id == project_id,
            MetricPoint.metric_id == metric_id,
            MetricPoint.interval == interval,
            MetricPoint.period_start >= start,
            MetricPoint.period_start <= end,
            MetricPoint.dimensions_hash == "",
        )
        .order_by(MetricPoint.period_start)
    )
    return list((await session.execute(q)).scalars().all())


async def query_batch_series(
    session: AsyncSession,
    project_id: str,
    metric_ids: list[str],
    start: date,
    end: date,
    interval: str = "month",
) -> dict[str, list[MetricPoint]]:
    out: dict[str, list[MetricPoint]] = {m: [] for m in metric_ids}
    if not metric_ids:
        return out
    q = (
        select(MetricPoint)
        .where(
            MetricPoint.project_id == project_id,
            MetricPoint.metric_id.in_(metric_ids),
            MetricPoint.interval == interval,
            MetricPoint.period_start >= start,
            MetricPoint.period_start <= end,
            MetricPoint.dimensions_hash == "",
        )
        .order_by(MetricPoint.metric_id, MetricPoint.period_start)
    )
    for pt in (await session.execute(q)).scalars().all():
        out.setdefault(pt.metric_id, []).append(pt)
    return out


async def compare_series(
    session: AsyncSession,
    project_ids: list[str],
    metric_id: str,
    start: date,
    end: date,
    interval: str = "month",
) -> dict[str, list[MetricPoint]]:
    out: dict[str, list[MetricPoint]] = {p: [] for p in project_ids}
    q = (
        select(MetricPoint)
        .where(
            MetricPoint.project_id.in_(project_ids),
            MetricPoint.metric_id == metric_id,
            MetricPoint.interval == interval,
            MetricPoint.period_start >= start,
            MetricPoint.period_start <= end,
            MetricPoint.dimensions_hash == "",
        )
        .order_by(MetricPoint.project_id, MetricPoint.period_start)
    )
    for pt in (await session.execute(q)).scalars().all():
        out.setdefault(pt.project_id, []).append(pt)
    return out


async def get_top_pages(
    session: AsyncSession,
    project_id: str,
    snapshot_type: str,
    period_start: date | None = None,
) -> PageSnapshot | None:
    q = select(PageSnapshot).where(
        PageSnapshot.project_id == project_id,
        PageSnapshot.snapshot_type == snapshot_type,
    )
    if period_start:
        q = q.where(PageSnapshot.period_start == period_start)
    q = q.order_by(PageSnapshot.period_start.desc()).limit(1)
    return (await session.execute(q)).scalar_one_or_none()


async def get_cohorts(
    session: AsyncSession,
    project_id: str,
    start: date | None = None,
    end: date | None = None,
) -> list[CohortPoint]:
    q = select(CohortPoint).where(CohortPoint.project_id == project_id).order_by(
        CohortPoint.cohort_month, CohortPoint.stage
    )
    if start:
        q = q.where(CohortPoint.cohort_month >= start)
    if end:
        q = q.where(CohortPoint.cohort_month <= end)
    return list((await session.execute(q)).scalars().all())


def points_to_export_rows(
    project_id: str,
    metric_id: str,
    interval: str,
    points: list[MetricPoint],
    definition: MetricDefinition | None,
) -> list[dict[str, Any]]:
    rows = []
    for p in points:
        rows.append(
            {
                "project_id": project_id,
                "metric_id": metric_id,
                "metric_name": definition.display_name if definition else metric_id,
                "interval": interval,
                "period_start": p.period_start.isoformat(),
                "value": p.value,
                "source": p.source,
                "definition": definition.definition if definition else None,
                "methodology": definition.methodology if definition else None,
                "caveats": definition.caveats if definition else None,
            }
        )
    return rows


def export_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "project_id,metric_id,interval,period_start,value\n"
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def export_json(rows: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> str:
    return json.dumps({"meta": meta or {}, "data": rows}, indent=2, default=str)


def normalize_value(value: float, mode: str | None, divisor: float | None) -> float:
    if not mode or mode == "raw" or not divisor or divisor == 0:
        return value
    if mode == "per_unit":
        return value / divisor
    return value


def parse_range(start: str | None, end: str | None) -> tuple[date, date]:
    from app.timeutil import months_back, utc_today

    e = parse_date(end) if end else utc_today()
    s = parse_date(start) if start else months_back(e, 24)
    return s, e
