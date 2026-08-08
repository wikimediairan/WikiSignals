from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

import app.models  # noqa: F401
from app import __version__
from app.api import api_router
from app.config import get_settings
from app.db.session import get_engine, init_engine
from app.models.ingestion import IngestionRun
from app.schemas.api import HealthOut
from app.security import SecurityHeadersMiddleware

STATIC_DIR = Path(__file__).parent / "static"
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    # Creating the engine must not block startup on a live DB connection.
    try:
        init_engine()
        logger.info(
            "WikiSignals starting env=%s default_project=%s",
            settings.environment,
            settings.default_project_id,
        )
    except Exception:
        logger.exception("Failed to init database engine — check DATABASE_URL")
        raise
    yield
    try:
        engine = get_engine()
        await engine.dispose()
    except Exception:
        logger.exception("Error disposing database engine")


def create_app() -> FastAPI:
    settings = get_settings()
    docs_url = "/docs" if settings.docs_enabled else None
    redoc_url = "/redoc" if settings.docs_enabled else None
    openapi_url = "/openapi.json" if settings.docs_enabled else None

    app = FastAPI(
        title=settings.app_name or "WikiSignals",
        version=settings.app_version or __version__,
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        description=(
            "WikiSignals — community health and capacity analytics for Wikimedia. "
            "Maintenance burden, administrative workload, governance queues, "
            "conflict signals, bot dependency, and capacity ratios. "
            "Official activity metrics are consumed from Wikimedia Analytics (Wikistats family) "
            "as context rather than reproduced as the product focus. "
            "Source: https://github.com/wikimediairan/WikiSignals"
        ),
    )
    app.add_middleware(SecurityHeadersMiddleware)
    # CORS: only configured origins (set to the Toolforge URL in production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,  # public read API; cookies not used
        allow_methods=["GET", "HEAD", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )
    app.include_router(api_router)

    @app.get("/health", response_model=HealthOut)
    async def health() -> HealthOut:
        index = STATIC_DIR / "index.html"
        last = None
        try:
            from app.db.session import async_session_factory

            if async_session_factory is not None:
                async with async_session_factory() as session:
                    q = (
                        select(IngestionRun)
                        .where(IngestionRun.status == "success")
                        .order_by(IngestionRun.finished_at.desc())
                        .limit(1)
                    )
                    row = (await session.execute(q)).scalar_one_or_none()
                    if row:
                        last = row.finished_at
        except Exception:  # noqa: BLE001
            logger.debug("Could not load last ingest time", exc_info=True)
        return HealthOut(
            status="ok",
            service="wikisignals",
            version=settings.app_version or __version__,
            frontend="built" if index.exists() else "missing",
            default_project_id=settings.default_project_id,
            last_successful_ingest=last,
        )

    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str) -> FileResponse:
            # Never serve SPA for API paths; block path traversal
            if full_path.startswith("api/") or ".." in full_path or full_path.startswith("/"):
                raise HTTPException(status_code=404)
            # Always revalidate index.html so deploys pick up new hashed JS without hard refresh
            return FileResponse(
                index_path,
                headers={
                    "Cache-Control": "no-cache, must-revalidate",
                },
            )
    else:
        logger.info("Frontend static files not built at %s (dev mode OK)", STATIC_DIR)

    return app


app = create_app()
