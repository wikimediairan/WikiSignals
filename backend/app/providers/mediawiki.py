"""MediaWiki Action API provider for logs, categories, and siteinfo."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urljoin

from app.config import Settings, get_settings
from app.providers.base import SeriesPoint, SeriesResult
from app.providers.http_client import RateLimitedClient
from app.timeutil import month_start, period_start_for

logger = logging.getLogger(__name__)


class MediaWikiProvider:
    name = "mediawiki"

    def __init__(self, settings: Settings | None = None, client: RateLimitedClient | None = None):
        self.settings = settings or get_settings()
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> MediaWikiProvider:
        if self._client is None:
            self._client = RateLimitedClient(self.settings)
            await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.__aexit__(*args)

    def api_url(self, domain: str) -> str:
        return urljoin(f"https://{domain}/", "w/api.php")

    async def siteinfo(self, domain: str) -> dict[str, Any]:
        assert self._client is not None
        data = await self._client.get_json(
            self.api_url(domain),
            params={
                "action": "query",
                "meta": "siteinfo",
                "siprop": "general|statistics|namespaces",
                "format": "json",
                "formatversion": "2",
            },
        )
        return (data or {}).get("query") or {}

    async def category_info(self, domain: str, category_title: str) -> dict[str, Any] | None:
        """Return categoryinfo for a category title (with or without Category:/رده: prefix)."""
        assert self._client is not None
        raw = (category_title or "").strip()
        if not raw:
            return None
        # Accept bare title, English Category:, or local namespace (e.g. رده:)
        candidates = [raw]
        lower = raw.lower()
        if not lower.startswith("category:") and ":" not in raw.split()[0]:
            candidates.append(f"Category:{raw}")
        for title in candidates:
            data = await self._client.get_json(
                self.api_url(domain),
                params={
                    "action": "query",
                    "prop": "categoryinfo",
                    "titles": title,
                    "format": "json",
                    "formatversion": "2",
                },
            )
            if not data:
                continue
            pages = ((data.get("query") or {}).get("pages")) or []
            if not pages:
                continue
            page = pages[0]
            if page.get("missing"):
                continue
            info = page.get("categoryinfo") or {}
            # Some pages exist but are not categories
            if not info and page.get("ns") != 14:
                continue
            return {
                "title": page.get("title"),
                "size": int(info.get("size") or 0),
                "pages": int(info.get("pages") or 0),
                "files": int(info.get("files") or 0),
                "subcats": int(info.get("subcats") or 0),
            }
        return None

    async def aggregate_logevents(
        self,
        domain: str,
        log_type: str,
        start: date,
        end: date,
        metric_id: str,
        interval: str = "month",
        max_pages: int = 40,
        action_filter: str | None = None,
    ) -> SeriesResult:
        """Aggregate logevents counts by period, optionally filtering by action."""
        assert self._client is not None
        le_start = datetime(start.year, start.month, start.day, tzinfo=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        le_end = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        params: dict[str, Any] = {
            "action": "query",
            "list": "logevents",
            "letype": log_type,
            "lelimit": "500",
            "ledir": "newer",
            "lestart": le_start,
            "leend": le_end,
            "format": "json",
            "formatversion": "2",
        }
        if action_filter:
            params["leaction"] = f"{log_type}/{action_filter}"

        counts: Counter[date] = Counter()
        action_breakdown: dict[str, int] = defaultdict(int)
        continuations = 0
        truncated = False
        while continuations < max_pages:
            data = await self._client.get_json(self.api_url(domain), params=params)
            if not data:
                break
            events = ((data.get("query") or {}).get("logevents")) or []
            for ev in events:
                action = ev.get("action") or "unknown"
                if action_filter and action != action_filter:
                    continue
                action_breakdown[action] += 1
                ts = ev.get("timestamp")
                if not ts:
                    continue
                d = date.fromisoformat(ts[:10])
                key = month_start(d) if interval == "month" else period_start_for(d, "day")  # type: ignore[arg-type]
                counts[key] += 1
            cont = data.get("continue")
            if not cont:
                break
            params.update(cont)
            continuations += 1
        else:
            truncated = True

        points = [SeriesPoint(period_start=k, value=float(v)) for k, v in sorted(counts.items())]
        return SeriesResult(
            metric_id=metric_id,
            points=points,
            source="mediawiki",
            raw={
                "quality": {
                    "truncated": truncated,
                    "pages_fetched": continuations + 1,
                    "action_breakdown": dict(action_breakdown),
                }
            },
        )

    async def aggregate_logevents_by_action(
        self,
        domain: str,
        log_type: str,
        start: date,
        end: date,
        interval: str = "month",
        max_pages: int = 40,
    ) -> dict[str, SeriesResult]:
        """Return per-action series for a log type (e.g. block/unblock)."""
        assert self._client is not None
        le_start = datetime(start.year, start.month, start.day, tzinfo=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        le_end = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        params: dict[str, Any] = {
            "action": "query",
            "list": "logevents",
            "letype": log_type,
            "lelimit": "500",
            "ledir": "newer",
            "lestart": le_start,
            "leend": le_end,
            "format": "json",
            "formatversion": "2",
        }
        buckets: dict[str, Counter[date]] = defaultdict(Counter)
        continuations = 0
        while continuations < max_pages:
            data = await self._client.get_json(self.api_url(domain), params=params)
            if not data:
                break
            events = ((data.get("query") or {}).get("logevents")) or []
            for ev in events:
                action = str(ev.get("action") or "unknown")
                ts = ev.get("timestamp")
                if not ts:
                    continue
                d = date.fromisoformat(ts[:10])
                key = month_start(d) if interval == "month" else period_start_for(d, "day")  # type: ignore[arg-type]
                buckets[action][key] += 1
            cont = data.get("continue")
            if not cont:
                break
            params.update(cont)
            continuations += 1

        out: dict[str, SeriesResult] = {}
        for action, counter in buckets.items():
            out[action] = SeriesResult(
                metric_id=f"log.{log_type}.{action}",
                points=[SeriesPoint(period_start=k, value=float(v)) for k, v in sorted(counter.items())],
                source="mediawiki",
            )
        return out
