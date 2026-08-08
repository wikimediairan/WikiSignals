from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.http_cache import set_public_cache
from app.models.health import BacklogSnapshot, ProcessSnapshot
from app.services import metrics as metric_service
from app.services.signals import build_health_signals
from app.timeutil import parse_date

router = APIRouter()


@router.get("/projects/{project_id}/health")
async def project_health(
    project_id: str,
    response: Response,
    end: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    set_public_cache(response)
    project = await metric_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    end_d = parse_date(end) if end else None
    return await build_health_signals(db, project, end=end_d)


@router.get("/projects/{project_id}/backlogs")
async def project_backlogs(
    project_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    set_public_cache(response)
    project = await metric_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    health = project.health_config or {}
    tracks_cfg = health.get("maintenance_tracks") or []
    # Latest snapshot per track
    snaps = (
        await db.execute(
            select(BacklogSnapshot)
            .where(BacklogSnapshot.project_id == project_id)
            .order_by(BacklogSnapshot.period_start.desc())
        )
    ).scalars().all()
    latest: dict[str, BacklogSnapshot] = {}
    for s in snaps:
        if s.track_id not in latest:
            latest[s.track_id] = s
    tracks_out = []
    for t in tracks_cfg:
        tid = t["id"]
        snap = latest.get(tid)
        tracks_out.append(
            {
                "id": tid,
                "label": t.get("label") or tid,
                "enabled": bool(t.get("enabled")),
                "kind": t.get("kind"),
                "category": t.get("category"),
                "notes": t.get("notes"),
                "latest": None
                if not snap
                else {
                    "period_start": snap.period_start.isoformat(),
                    "open_count": snap.open_count,
                    "net": snap.net,
                    "source": snap.source,
                    "meta": snap.meta,
                },
            }
        )
    return {
        "project_id": project_id,
        "tracks": tracks_out,
        "note": "Only configured tracks appear. Set categories in project health config after local verification.",
    }


@router.get("/projects/{project_id}/processes")
async def project_processes(
    project_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    set_public_cache(response)
    project = await metric_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    health = project.health_config or {}
    tracks_cfg = health.get("process_tracks") or []
    snaps = (
        await db.execute(
            select(ProcessSnapshot)
            .where(ProcessSnapshot.project_id == project_id)
            .order_by(ProcessSnapshot.period_start.desc())
        )
    ).scalars().all()
    latest: dict[str, ProcessSnapshot] = {}
    for s in snaps:
        if s.track_id not in latest:
            latest[s.track_id] = s
    tracks_out = []
    for t in tracks_cfg:
        tid = t["id"]
        snap = latest.get(tid)
        tracks_out.append(
            {
                "id": tid,
                "label": t.get("label") or tid,
                "enabled": bool(t.get("enabled")),
                "kind": t.get("kind"),
                "category": t.get("category"),
                "notes": t.get("notes"),
                "latest": None
                if not snap
                else {
                    "period_start": snap.period_start.isoformat(),
                    "open_count": snap.open_count,
                    "median_days": snap.median_days,
                    "source": snap.source,
                    "meta": snap.meta,
                },
            }
        )
    return {
        "project_id": project_id,
        "tracks": tracks_out,
        "note": "Process queues are project-specific. Configure process_tracks in YAML.",
    }
