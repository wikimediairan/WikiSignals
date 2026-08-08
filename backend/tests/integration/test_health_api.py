from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.pipeline.store import upsert_series
from app.providers.base import SeriesPoint, SeriesResult


@pytest.mark.asyncio
async def test_health_endpoint_shape(client, engine):
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await upsert_series(
            session,
            "fa.wikipedia",
            SeriesResult(
                metric_id="editors.active",
                points=[
                    SeriesPoint(date(2026, 1, 1), 700),
                    SeriesPoint(date(2026, 2, 1), 750),
                ],
                source="test",
            ),
            "month",
        )
    resp = await client.get("/api/v1/projects/fa.wikipedia/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "signals" in body
    assert "context" in body
    assert "disclaimer" in body
    assert "not a community health grade" in body["disclaimer"].lower() or "grade" in body["disclaimer"].lower()
    # active editors should appear
    ids = {s["id"] for s in body["signals"] + body["context"]}
    assert "editors.active" in ids


@pytest.mark.asyncio
async def test_backlogs_and_processes_endpoints(client):
    r1 = await client.get("/api/v1/projects/fa.wikipedia/backlogs")
    assert r1.status_code == 200
    assert "tracks" in r1.json()
    r2 = await client.get("/api/v1/projects/fa.wikipedia/processes")
    assert r2.status_code == 200
    assert "tracks" in r2.json()


@pytest.mark.asyncio
async def test_cohorts_deprecated_header(client):
    resp = await client.get("/api/v1/projects/fa.wikipedia/cohorts")
    assert resp.status_code == 200
    assert resp.headers.get("deprecation") == "true"
