from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.http_cache import set_public_cache
from app.security import is_safe_metric_id, is_safe_project_id
from app.schemas.api import (
    BatchMetricsOut,
    CohortOut,
    CohortsResponse,
    CohortStageOut,
    MetricDefinitionOut,
    MetricSeriesOut,
    SeriesPointOut,
    TopPagesOut,
)
from app.services import metrics as metric_service
from app.timeutil import parse_date

router = APIRouter()


def _cache_headers(response: Response) -> None:
    set_public_cache(response)


def _series_out(
    project_id: str,
    metric_id: str,
    interval: str,
    start,
    end,
    points,
    definition,
) -> MetricSeriesOut:
    """
    Series `status` is about *this response* (has data or not).

    Catalog may mark metrics as `unavailable_without_replicas` as a capability
    flag on the definition; that must not appear as a badge once points exist.
    """
    def_status = definition.status if definition else "unknown"
    unavailable_reason = None

    if points:
        # Live series is available; capability flags stay on definition only.
        if def_status in ("unavailable_without_replicas", "unavailable"):
            status = "stable"
        else:
            status = def_status
    elif def_status == "unavailable_without_replicas":
        status = "unavailable"
        unavailable_reason = (
            "This metric requires Toolforge wiki replicas and stored series points. "
            "Set WIKI_REPLICAS_ENABLED/HOST/USER/PASSWORD, then run "
            "`collect-replicas` (backfill) or `daily` (recent months). "
            "collect-health does not fill reverts."
        )
    else:
        status = def_status

    return MetricSeriesOut(
        project_id=project_id,
        metric_id=metric_id,
        interval=interval,
        start=start,
        end=end,
        status=status,
        definition=MetricDefinitionOut.model_validate(definition) if definition else None,
        points=[SeriesPointOut(period_start=p.period_start, value=p.value, source=p.source) for p in points],
        unavailable_reason=unavailable_reason,
    )


@router.get("/metrics/definitions", response_model=list[MetricDefinitionOut])
async def list_definitions(response: Response, db: AsyncSession = Depends(get_db)) -> list[MetricDefinitionOut]:
    _cache_headers(response)
    defs = await metric_service.list_metric_definitions(db)
    return [MetricDefinitionOut.model_validate(d) for d in defs]


@router.get(
    "/projects/{project_id}/metrics/{metric_id}",
    response_model=MetricSeriesOut,
)
async def get_metric_series(
    project_id: str,
    metric_id: str,
    response: Response,
    start: str | None = None,
    end: str | None = None,
    interval: str = Query("month", pattern="^(day|week|month|quarter|year)$"),
    db: AsyncSession = Depends(get_db),
) -> MetricSeriesOut:
    _cache_headers(response)
    if not is_safe_project_id(project_id) or not is_safe_metric_id(metric_id):
        raise HTTPException(status_code=400, detail="Invalid project or metric id")
    project = await metric_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    definition = await metric_service.get_metric_definition(db, metric_id)
    s, e = metric_service.parse_range(start, end)
    points = await metric_service.query_series(db, project_id, metric_id, s, e, interval)
    return _series_out(project_id, metric_id, interval, s, e, points, definition)


@router.get("/projects/{project_id}/metrics", response_model=BatchMetricsOut)
async def get_batch_metrics(
    project_id: str,
    response: Response,
    ids: str = Query(..., description="Comma-separated metric IDs"),
    start: str | None = None,
    end: str | None = None,
    interval: str = Query("month", pattern="^(day|week|month|quarter|year)$"),
    db: AsyncSession = Depends(get_db),
) -> BatchMetricsOut:
    _cache_headers(response)
    project = await metric_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    metric_ids = [m.strip() for m in ids.split(",") if m.strip()]
    s, e = metric_service.parse_range(start, end)
    batch = await metric_service.query_batch_series(db, project_id, metric_ids, s, e, interval)
    series: dict[str, MetricSeriesOut] = {}
    for mid in metric_ids:
        definition = await metric_service.get_metric_definition(db, mid)
        series[mid] = _series_out(project_id, mid, interval, s, e, batch.get(mid, []), definition)
    return BatchMetricsOut(project_id=project_id, interval=interval, start=s, end=e, series=series)


@router.get("/projects/{project_id}/top-pages", response_model=TopPagesOut)
async def top_pages(
    project_id: str,
    response: Response,
    snapshot_type: str = Query("top_by_edits", pattern="^(top_by_edits|top_by_pageviews)$"),
    period: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> TopPagesOut:
    _cache_headers(response)
    project = await metric_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    period_start = parse_date(period) if period else None
    snap = await metric_service.get_top_pages(db, project_id, snapshot_type, period_start)
    if not snap:
        return TopPagesOut(
            project_id=project_id,
            snapshot_type=snapshot_type,
            period_start=period_start,
            items=[],
            source=None,
        )
    return TopPagesOut(
        project_id=project_id,
        snapshot_type=snapshot_type,
        period_start=snap.period_start,
        items=list(snap.payload or []),
        source=snap.source,
    )


@router.get("/projects/{project_id}/cohorts", response_model=CohortsResponse)
async def cohorts(
    project_id: str,
    response: Response,
    start: str | None = None,
    end: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> CohortsResponse:
    _cache_headers(response)
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = (
        '</methodology>; rel="deprecation"; type="text/html", '
        '<https://meta.wikimedia.org/wiki/Wikistats>; rel="related"'
    )
    project = await metric_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    s = parse_date(start) if start else None
    e = parse_date(end) if end else None
    points = await metric_service.get_cohorts(db, project_id, s, e)
    if not points:
        return CohortsResponse(
            project_id=project_id,
            available=False,
            reason=(
                "Deprecated in WikiSignals primary surface. "
                "Detailed newcomer cohorts belong to the New Editor Health Dashboard. "
                "Replica-backed data may still be stored when configured."
            ),
            cohorts=[],
        )
    by_month: dict = {}
    for p in points:
        by_month.setdefault(p.cohort_month, []).append(
            CohortStageOut(stage=p.stage, value=p.value)
        )
    cohorts_out = [
        CohortOut(project_id=project_id, cohort_month=m, stages=stages)
        for m, stages in sorted(by_month.items())
    ]
    return CohortsResponse(project_id=project_id, available=True, reason=None, cohorts=cohorts_out)
