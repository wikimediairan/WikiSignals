"""Wikimedia Analytics Query Service (AQS) provider."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.config import Settings, get_settings
from app.providers.base import SeriesPoint, SeriesResult
from app.providers.http_client import RateLimitedClient
from app.timeutil import aqs_date_token, aqs_pageviews_token, next_month_start

logger = logging.getLogger(__name__)

# Activity levels for editor distribution and active-editor composition.
ACTIVITY_LEVELS = {
    "1..4-edits": "editors.activity_1_4",
    "5..24-edits": "editors.activity_5_24",
    "25..99-edits": "editors.activity_25_99",
    "100..-edits": "editors.highly_active",
}

EDITOR_TYPES_EDITS = {
    "all-editor-types": "edits.total",
    "user": "edits.user",
    "group-bot": "edits.group_bot",
    "name-bot": "edits.name_bot",
    "anonymous": "edits.anonymous",
}


def _items_from_aqs(payload: Any) -> list[dict[str, Any]]:
    if not payload:
        return []
    items = payload.get("items") if isinstance(payload, dict) else None
    if not items:
        return []
    # Some endpoints nest results under items[0].results
    if len(items) == 1 and isinstance(items[0], dict) and "results" in items[0]:
        return list(items[0]["results"])
    # pageviews aggregate: items are the points
    return list(items)


def _parse_timestamp(ts: str) -> date:
    # Formats: 2024010100, 20240101, 2024-01-01T00:00:00.000Z
    clean = ts.replace("-", "").replace("T", "").replace(":", "").replace("Z", "")
    return date(int(clean[0:4]), int(clean[4:6]), int(clean[6:8]))


def _points_from_items(items: list[dict[str, Any]], value_keys: tuple[str, ...] = ("edits", "editors", "views", "devices", "net_sum", "absolute_bytes_diff", "new_registered_users", "edited_pages", "count")) -> list[SeriesPoint]:
    points: list[SeriesPoint] = []
    for item in items:
        ts = item.get("timestamp") or item.get("date")
        if not ts:
            continue
        value = None
        for key in value_keys:
            if key in item and item[key] is not None:
                value = float(item[key])
                break
        if value is None:
            # unique devices uses "devices"
            if "devices" in item:
                value = float(item["devices"])
            else:
                continue
        points.append(SeriesPoint(period_start=_parse_timestamp(str(ts)), value=value))
    return points


class AQSProvider:
    name = "aqs"

    def __init__(
        self,
        settings: Settings | None = None,
        client: RateLimitedClient | None = None,
    ):
        self.settings = settings or get_settings()
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> AQSProvider:
        if self._client is None:
            self._client = RateLimitedClient(self.settings)
            await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.__aexit__(*args)

    async def close(self) -> None:
        await self.__aexit__(None, None, None)

    def _url(self, *parts: str) -> str:
        base = self.settings.aqs_base_url.rstrip("/")
        return "/".join([base, *[p.strip("/") for p in parts]])

    async def _get_series(
        self,
        metric_id: str,
        *path_parts: str,
        value_keys: tuple[str, ...] = ("edits", "editors", "views", "devices", "new_registered_users", "edited_pages"),
    ) -> SeriesResult:
        assert self._client is not None
        url = self._url(*path_parts)
        payload = await self._client.get_json(url)
        items = _items_from_aqs(payload)
        points = _points_from_items(items, value_keys=value_keys)
        return SeriesResult(metric_id=metric_id, points=points, source="aqs", raw=payload)

    @staticmethod
    def _range_end(start: date, end: date, granularity: str) -> date:
        """AQS requires end > start; for a single month use next month start."""
        if end > start:
            return end
        if granularity == "monthly":
            return next_month_start(start)
        return end if end > start else date(start.year, start.month, min(start.day + 1, 28))

    async def fetch_edits(
        self,
        aqs_project: str,
        start: date,
        end: date,
        granularity: str = "monthly",
        editor_type: str = "all-editor-types",
        page_type: str = "all-page-types",
        metric_id: str | None = None,
    ) -> SeriesResult:
        mid = metric_id or EDITOR_TYPES_EDITS.get(editor_type, f"edits.{editor_type}")
        end = self._range_end(start, end, granularity)
        return await self._get_series(
            mid,
            "edits/aggregate",
            aqs_project,
            editor_type,
            page_type,
            granularity,
            aqs_date_token(start, granularity),
            aqs_date_token(end, granularity),
            value_keys=("edits",),
        )

    async def fetch_editors(
        self,
        aqs_project: str,
        start: date,
        end: date,
        activity_level: str,
        metric_id: str,
        granularity: str = "monthly",
        editor_type: str = "user",
        page_type: str = "all-page-types",
    ) -> SeriesResult:
        end = self._range_end(start, end, granularity)
        return await self._get_series(
            metric_id,
            "editors/aggregate",
            aqs_project,
            editor_type,
            page_type,
            activity_level,
            granularity,
            aqs_date_token(start, granularity),
            aqs_date_token(end, granularity),
            value_keys=("editors",),
        )

    async def fetch_new_registered_users(
        self,
        aqs_project: str,
        start: date,
        end: date,
        granularity: str = "monthly",
    ) -> SeriesResult:
        end = self._range_end(start, end, granularity)
        return await self._get_series(
            "editors.new_accounts",
            "registered-users/new",
            aqs_project,
            granularity,
            aqs_date_token(start, granularity),
            aqs_date_token(end, granularity),
            value_keys=("new_registered_users",),
        )

    async def fetch_new_pages(
        self,
        aqs_project: str,
        start: date,
        end: date,
        page_type: str = "all-page-types",
        metric_id: str = "content.pages_created",
        granularity: str = "monthly",
        editor_type: str = "all-editor-types",
    ) -> SeriesResult:
        end = self._range_end(start, end, granularity)
        return await self._get_series(
            metric_id,
            "edited-pages/new",
            aqs_project,
            editor_type,
            page_type,
            granularity,
            aqs_date_token(start, granularity),
            aqs_date_token(end, granularity),
            value_keys=("new_pages", "edited_pages", "count"),
        )

    async def fetch_edited_pages(
        self,
        aqs_project: str,
        start: date,
        end: date,
        granularity: str = "monthly",
        editor_type: str = "all-editor-types",
        page_type: str = "all-page-types",
        activity_level: str = "all-activity-levels",
    ) -> SeriesResult:
        end = self._range_end(start, end, granularity)
        return await self._get_series(
            "content.pages_edited",
            "edited-pages/aggregate",
            aqs_project,
            editor_type,
            page_type,
            activity_level,
            granularity,
            aqs_date_token(start, granularity),
            aqs_date_token(end, granularity),
            value_keys=("edited_pages",),
        )

    async def fetch_pageviews(
        self,
        pageviews_project: str,
        start: date,
        end: date,
        granularity: str = "monthly",
        access: str = "all-access",
        agent: str = "user",
    ) -> SeriesResult:
        # pageviews uses YYYYMMDD00 tokens
        g = "monthly" if granularity == "monthly" else "daily"
        end = self._range_end(start, end, g)
        return await self._get_series(
            "readers.pageviews",
            "pageviews/aggregate",
            pageviews_project,
            access,
            agent,
            g,
            aqs_pageviews_token(start),
            aqs_pageviews_token(end),
            value_keys=("views",),
        )

    async def fetch_unique_devices(
        self,
        aqs_project: str,
        start: date,
        end: date,
        granularity: str = "monthly",
        sites: str = "all-sites",
    ) -> SeriesResult:
        g = "monthly" if granularity == "monthly" else "daily"
        end = self._range_end(start, end, g)
        return await self._get_series(
            "readers.unique_devices",
            "unique-devices",
            aqs_project,
            sites,
            g,
            aqs_date_token(start, g),
            aqs_date_token(end, g),
            value_keys=("devices",),
        )

    async def fetch_top_pages_by_edits(
        self,
        aqs_project: str,
        year: int,
        month: int,
        editor_type: str = "all-editor-types",
        page_type: str = "content",
    ) -> list[dict[str, Any]]:
        assert self._client is not None
        url = self._url(
            "edited-pages/top-by-edits",
            aqs_project,
            editor_type,
            page_type,
            f"{year:04d}",
            f"{month:02d}",
            "all-days",
        )
        payload = await self._client.get_json(url)
        if not payload:
            return []
        items = payload.get("items") or []
        if not items:
            return []
        top = items[0].get("results") or items[0].get("top") or []
        # normalize
        out = []
        for row in top:
            out.append(
                {
                    "page_title": row.get("page_title") or row.get("page") or row.get("article"),
                    "edits": row.get("edits") or row.get("edit_count"),
                    "rank": row.get("rank"),
                }
            )
        return out

    async def fetch_top_pageviews(
        self,
        pageviews_project: str,
        year: int,
        month: int,
        access: str = "all-access",
    ) -> list[dict[str, Any]]:
        assert self._client is not None
        url = self._url(
            "pageviews/top",
            pageviews_project,
            access,
            f"{year:04d}",
            f"{month:02d}",
            "all-days",
        )
        payload = await self._client.get_json(url)
        if not payload:
            return []
        items = payload.get("items") or []
        if not items:
            return []
        articles = items[0].get("articles") or []
        return [
            {
                "page_title": a.get("article"),
                "views": a.get("views"),
                "rank": a.get("rank"),
            }
            for a in articles
        ]

    async def fetch_core_monthly(
        self,
        aqs_project: str,
        pageviews_project: str,
        start: date,
        end: date,
    ) -> list[SeriesResult]:
        """Fetch the stable monthly AQS suite for one project."""
        results: list[SeriesResult] = []
        g = "monthly"

        for editor_type, metric_id in EDITOR_TYPES_EDITS.items():
            results.append(
                await self.fetch_edits(
                    aqs_project, start, end, granularity=g, editor_type=editor_type, metric_id=metric_id
                )
            )

        activity_series: dict[str, SeriesResult] = {}
        for level, metric_id in ACTIVITY_LEVELS.items():
            series = await self.fetch_editors(
                aqs_project, start, end, activity_level=level, metric_id=metric_id, granularity=g
            )
            activity_series[metric_id] = series
            results.append(series)

        # Active editors = sum of 5..24 + 25..99 + 100..
        active = _sum_series(
            "editors.active",
            [
                activity_series["editors.activity_5_24"],
                activity_series["editors.activity_25_99"],
                activity_series["editors.highly_active"],
            ],
        )
        results.append(active)

        results.append(await self.fetch_new_registered_users(aqs_project, start, end, g))
        results.append(
            await self.fetch_new_pages(
                aqs_project, start, end, page_type="all-page-types", metric_id="content.pages_created", granularity=g
            )
        )
        results.append(
            await self.fetch_new_pages(
                aqs_project,
                start,
                end,
                page_type="content",
                metric_id="content.pages_created_content",
                granularity=g,
            )
        )
        results.append(await self.fetch_edited_pages(aqs_project, start, end, granularity=g))
        results.append(await self.fetch_pageviews(pageviews_project, start, end, granularity=g))
        results.append(await self.fetch_unique_devices(aqs_project, start, end, granularity=g))
        return results


def _sum_series(metric_id: str, series_list: list[SeriesResult]) -> SeriesResult:
    totals: dict[date, float] = {}
    for series in series_list:
        for p in series.points:
            totals[p.period_start] = totals.get(p.period_start, 0.0) + p.value
    points = [SeriesPoint(period_start=k, value=v) for k, v in sorted(totals.items())]
    return SeriesResult(metric_id=metric_id, points=points, source="aqs-derived")
