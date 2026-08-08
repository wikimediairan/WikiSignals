"""Administrative log aggregation (blocks, protect, delete, move, rights)."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.pipeline.store import upsert_series
from app.providers.base import SeriesPoint, SeriesResult
from app.providers.mediawiki import MediaWikiProvider
from app.timeutil import months_back, utc_today

logger = logging.getLogger(__name__)


def _metric_for(log_type: str, action: str) -> str | None:
    if log_type == "block":
        if action == "block":
            return "admin.blocks"
        if action == "unblock":
            return "admin.unblocks"
    if log_type == "protect":
        if action in ("protect", "modify"):
            return "admin.protections"
        if action == "unprotect":
            return "admin.unprotections"
    if log_type == "delete":
        if action == "delete":
            return "admin.deletions"
        if action == "restore":
            return "admin.undeletions"
    if log_type == "move":
        return "admin.moves"
    if log_type == "rights":
        return "admin.rights_changes"
    return None


async def collect_admin_logs(
    session: AsyncSession,
    project: Project,
    start: date | None = None,
    end: date | None = None,
    mw: MediaWikiProvider | None = None,
    max_pages: int | None = None,
) -> dict[str, Any]:
    end = end or utc_today()
    start = start or months_back(end, 6)
    owns = mw is None
    if mw is None:
        mw = MediaWikiProvider()
        await mw.__aenter__()

    # Default low page budget; daily job can pass an even smaller value
    page_budget = 15 if max_pages is None else max(1, min(max_pages, 40))

    merged: dict[str, dict[date, float]] = defaultdict(lambda: defaultdict(float))
    errors: dict[str, str] = {}
    try:
        for log_type in ("block", "protect", "delete", "move", "rights"):
            try:
                by_action = await mw.aggregate_logevents_by_action(
                    project.domain,
                    log_type,
                    start,
                    end,
                    interval="month",
                    max_pages=page_budget,
                )
            except Exception as exc:  # noqa: BLE001 — continue other log types
                logger.warning("admin log fetch failed for %s/%s: %s", project.id, log_type, exc)
                errors[log_type] = str(exc)
                continue
            for action, series in by_action.items():
                metric_id = _metric_for(log_type, action)
                if not metric_id:
                    continue
                for p in series.points:
                    merged[metric_id][p.period_start] += p.value

        written: dict[str, int] = {}
        totals: dict[date, float] = defaultdict(float)
        for metric_id, by_period in merged.items():
            points = [SeriesPoint(period_start=k, value=v) for k, v in sorted(by_period.items())]
            n = await upsert_series(
                session,
                project.id,
                SeriesResult(metric_id=metric_id, points=points, source="mediawiki"),
                "month",
            )
            written[metric_id] = n
            for p in points:
                totals[p.period_start] += p.value

        if totals:
            await upsert_series(
                session,
                project.id,
                SeriesResult(
                    metric_id="admin.actions_total",
                    points=[SeriesPoint(period_start=k, value=v) for k, v in sorted(totals.items())],
                    source="derived",
                ),
                "month",
            )
        return {
            "project_id": project.id,
            "written": written,
            "errors": errors,
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
    finally:
        if owns:
            await mw.__aexit__(None, None, None)
