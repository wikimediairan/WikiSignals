from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.metric import MetricPoint
from app.providers.base import SeriesPoint, SeriesResult
from app.pipeline.store import upsert_series


@pytest.mark.asyncio
async def test_projects_list_includes_default(client, session):
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 200
    data = resp.json()
    ids = [p["id"] for p in data]
    assert "fa.wikipedia" in ids
    default = next(p for p in data if p["default_for_workspace"])
    assert default["id"] == "fa.wikipedia"


@pytest.mark.asyncio
async def test_metric_series_and_export(client, engine):
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        series = SeriesResult(
            metric_id="editors.active",
            points=[
                SeriesPoint(date(2024, 1, 1), 100),
                SeriesPoint(date(2024, 2, 1), 110),
            ],
            source="test",
        )
        await upsert_series(session, "fa.wikipedia", series, "month")

    resp = await client.get(
        "/api/v1/projects/fa.wikipedia/metrics/editors.active",
        params={"start": "2024-01-01", "end": "2024-02-01", "interval": "month"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["metric_id"] == "editors.active"
    assert len(body["points"]) == 2
    assert body["points"][0]["value"] == 100

    exp = await client.get(
        "/api/v1/export",
        params={
            "projects": "fa.wikipedia",
            "metrics": "editors.active",
            "start": "2024-01-01",
            "end": "2024-02-01",
            "format": "csv",
        },
    )
    assert exp.status_code == 200
    assert "editors.active" in exp.text


@pytest.mark.asyncio
async def test_compare_disclaimer(client, engine):
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        for pid, val in (("fa.wikipedia", 100), ("tr.wikipedia", 80)):
            await upsert_series(
                session,
                pid,
                SeriesResult(
                    metric_id="edits.total",
                    points=[SeriesPoint(date(2024, 1, 1), val)],
                    source="test",
                ),
                "month",
            )
    resp = await client.get(
        "/api/v1/compare",
        params={
            "projects": "fa.wikipedia,tr.wikipedia",
            "metric": "edits.total",
            "start": "2024-01-01",
            "end": "2024-01-01",
        },
    )
    assert resp.status_code == 200
    assert "do not make one community better" in resp.json()["disclaimer"].lower()


@pytest.mark.asyncio
async def test_cohorts_unavailable_without_data(client):
    resp = await client.get("/api/v1/projects/fa.wikipedia/cohorts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    reason = (body["reason"] or "").lower()
    assert "replicas" in reason or "deprecated" in reason or "new editor" in reason


@pytest.mark.asyncio
async def test_methodology(client):
    resp = await client.get("/api/v1/methodology")
    assert resp.status_code == 200
    body = resp.json()
    assert body["timezone"] == "UTC"
    assert any(m["id"] == "editors.active" for m in body["metrics"])


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "wikisignals"
