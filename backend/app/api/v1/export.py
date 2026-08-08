from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.security import is_safe_metric_id, is_safe_project_id
from app.services import metrics as metric_service

router = APIRouter()


@router.get("/export")
async def export_metrics(
    projects: str = Query(..., description="Comma-separated project IDs"),
    metrics: str = Query(..., description="Comma-separated metric IDs"),
    start: str | None = None,
    end: str | None = None,
    interval: str = Query("month"),
    format: str = Query("csv", pattern="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    project_ids = [p.strip() for p in projects.split(",") if p.strip()]
    metric_ids = [m.strip() for m in metrics.split(",") if m.strip()]
    if len(project_ids) > 10 or len(metric_ids) > 40:
        raise HTTPException(status_code=400, detail="Too many projects or metrics in one export")
    for pid in project_ids:
        if not is_safe_project_id(pid):
            raise HTTPException(status_code=400, detail=f"Invalid project id: {pid}")
    for mid in metric_ids:
        if not is_safe_metric_id(mid):
            raise HTTPException(status_code=400, detail=f"Invalid metric id: {mid}")
    s, e = metric_service.parse_range(start, end)
    if e - s > timedelta(days=366 * 10):
        raise HTTPException(status_code=400, detail="Export range too large (max 10 years)")
    rows = []
    for pid in project_ids:
        if not await metric_service.get_project(db, pid):
            raise HTTPException(status_code=404, detail=f"Project not found: {pid}")
        for mid in metric_ids:
            definition = await metric_service.get_metric_definition(db, mid)
            points = await metric_service.query_series(db, pid, mid, s, e, interval)
            rows.extend(metric_service.points_to_export_rows(pid, mid, interval, points, definition))
    meta = {
        "projects": project_ids,
        "metrics": metric_ids,
        "interval": interval,
        "start": s.isoformat(),
        "end": e.isoformat(),
        "timezone": "UTC",
        "note": "Aggregated public Wikimedia contribution metrics. See methodology for definitions.",
    }
    if format == "json":
        body = metric_service.export_json(rows, meta=meta)
        return Response(content=body, media_type="application/json")
    body = metric_service.export_csv(rows)
    return PlainTextResponse(content=body, media_type="text/csv")
