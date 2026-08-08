from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.schemas.api import CompareOut, SeriesPointOut
from app.services import metrics as metric_service

router = APIRouter()

DISCLAIMER = (
    "Cross-project comparisons show activity volume under a shared metric definition. "
    "Raw editor or edit counts do not make one community better or healthier than another. "
    "Communities differ in size, language reach, content scope, and contribution culture."
)


@router.get("/compare", response_model=CompareOut)
async def compare_projects(
    response: Response,
    projects: str = Query(..., description="Comma-separated project IDs"),
    metric: str = Query(..., description="Metric ID"),
    start: str | None = None,
    end: str | None = None,
    interval: str = Query("month", pattern="^(day|week|month|quarter|year)$"),
    normalize: str | None = Query(None, description="raw (default) or leave empty"),
    db: AsyncSession = Depends(get_db),
) -> CompareOut:
    settings = get_settings()
    response.headers["Cache-Control"] = f"public, max-age={settings.public_cache_max_age_seconds}"
    project_ids = [p.strip() for p in projects.split(",") if p.strip()]
    if len(project_ids) < 1:
        raise HTTPException(status_code=400, detail="At least one project is required")
    for pid in project_ids:
        if not await metric_service.get_project(db, pid):
            raise HTTPException(status_code=404, detail=f"Project not found: {pid}")
    s, e = metric_service.parse_range(start, end)
    raw = await metric_service.compare_series(db, project_ids, metric, s, e, interval)
    series = {
        pid: [SeriesPointOut(period_start=p.period_start, value=p.value, source=p.source) for p in pts]
        for pid, pts in raw.items()
    }
    return CompareOut(
        metric_id=metric,
        interval=interval,
        start=s,
        end=e,
        normalize=normalize or "raw",
        disclaimer=DISCLAIMER,
        series=series,
    )
