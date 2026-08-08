from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.collectors.maintenance import collect_maintenance_backlogs
from app.models.project import Project


@pytest.mark.asyncio
async def test_maintenance_skips_disabled_and_missing_category(session):
    project = await session.get(Project, "fa.wikipedia")
    assert project is not None
    # Ensure empty enabled tracks -> open_total not required
    project.health_config = {
        "maintenance_tracks": [
            {"id": "x", "kind": "category", "category": None, "enabled": True, "label": "X"},
            {"id": "y", "kind": "category", "category": "DoesNotExistXYZ", "enabled": True, "label": "Y"},
        ]
    }
    await session.commit()

    mw = MagicMock()
    mw.category_info = AsyncMock(return_value=None)
    result = await collect_maintenance_backlogs(
        session, project, period=date(2026, 1, 1), mw=mw
    )
    assert result["open_total"] == 0.0
    assert all(t["status"] == "unavailable" for t in result["tracks"])


@pytest.mark.asyncio
async def test_maintenance_counts_category(session):
    project = await session.get(Project, "fa.wikipedia")
    project.health_config = {
        "maintenance_tracks": [
            {
                "id": "needs_citations",
                "kind": "category",
                "category": "TestCat",
                "enabled": True,
                "label": "Test",
            }
        ]
    }
    await session.commit()

    mw = MagicMock()
    mw.category_info = AsyncMock(
        return_value={"title": "Category:TestCat", "size": 10, "pages": 42, "files": 0, "subcats": 0}
    )
    result = await collect_maintenance_backlogs(
        session, project, period=date(2026, 1, 1), mw=mw
    )
    assert result["open_total"] == 42.0
    assert result["tracks"][0]["status"] == "ok"
