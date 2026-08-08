from fastapi import APIRouter

from app.api.v1 import annotations, compare, export, health, metrics, methodology, projects

router = APIRouter()
router.include_router(projects.router, tags=["projects"])
router.include_router(metrics.router, tags=["metrics"])
router.include_router(health.router, tags=["health"])
router.include_router(compare.router, tags=["compare"])
router.include_router(export.router, tags=["export"])
router.include_router(methodology.router, tags=["methodology"])
router.include_router(annotations.router, tags=["annotations"])
