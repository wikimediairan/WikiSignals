from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.api import ProjectOut
from app.security import is_safe_project_id
from app.services import metrics as metric_service

router = APIRouter()


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)) -> list[ProjectOut]:
    projects = await metric_service.list_projects(db)
    return [ProjectOut.model_validate(p) for p in projects]


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)) -> ProjectOut:
    if not is_safe_project_id(project_id):
        raise HTTPException(status_code=400, detail="Invalid project id")
    project = await metric_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return ProjectOut.model_validate(project)
