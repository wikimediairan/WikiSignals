"""Live smoke tests against public Wikimedia AQS (network required)."""

from datetime import date

import pytest

from app.config import get_settings
from app.providers.aqs import AQSProvider

pytestmark = pytest.mark.smoke


@pytest.mark.asyncio
async def test_live_fa_wikipedia_editors_shape():
    settings = get_settings()
    async with AQSProvider(settings) as aqs:
        series = await aqs.fetch_editors(
            "fa.wikipedia.org",
            date(2024, 1, 1),
            date(2024, 3, 1),
            activity_level="5..24-edits",
            metric_id="editors.activity_5_24",
        )
    assert series.points, "expected AQS to return editor counts for fa.wikipedia"
    for p in series.points:
        assert p.value >= 0
        assert p.period_start.day == 1


@pytest.mark.asyncio
async def test_live_fa_pageviews_shape():
    settings = get_settings()
    async with AQSProvider(settings) as aqs:
        series = await aqs.fetch_pageviews(
            "fa.wikipedia",
            date(2024, 1, 1),
            date(2024, 3, 1),
        )
    assert series.points
    assert all(p.value > 0 for p in series.points)
