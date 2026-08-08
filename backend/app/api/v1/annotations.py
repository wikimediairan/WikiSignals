from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.models.annotation import Annotation
from app.schemas.api import AnnotationOut

router = APIRouter()


@router.get("/annotations", response_model=list[AnnotationOut])
async def list_annotations(
    response: Response,
    project_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> list[AnnotationOut]:
    settings = get_settings()
    response.headers["Cache-Control"] = f"public, max-age={settings.public_cache_max_age_seconds}"
    q = select(Annotation).order_by(Annotation.start_date)
    if project_id:
        q = q.where((Annotation.project_id == project_id) | (Annotation.project_id.is_(None)))
    rows = list((await db.execute(q)).scalars().all())
    return [AnnotationOut.model_validate(r) for r in rows]


@router.get("/projects/{project_id}/annotations", response_model=list[AnnotationOut])
async def project_annotations(
    project_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> list[AnnotationOut]:
    settings = get_settings()
    response.headers["Cache-Control"] = f"public, max-age={settings.public_cache_max_age_seconds}"
    q = (
        select(Annotation)
        .where((Annotation.project_id == project_id) | (Annotation.project_id.is_(None)))
        .order_by(Annotation.start_date)
    )
    rows = list((await db.execute(q)).scalars().all())
    return [AnnotationOut.model_validate(r) for r in rows]
