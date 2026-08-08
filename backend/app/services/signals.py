"""Derived health signals and transparent threshold classification."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.pipeline.store import upsert_series
from app.providers.base import SeriesPoint, SeriesResult
from app.services import metrics as metric_service
from app.timeutil import add_interval, month_start, months_back, utc_today

SignalStatus = Literal["improving", "stable", "needs_attention", "unavailable"]


def classify_mom(
    change_pct: float | None,
    attention_above: float = 15.0,
    improving_below: float = -5.0,
) -> SignalStatus:
    if change_pct is None:
        return "unavailable"
    if change_pct >= attention_above:
        return "needs_attention"
    if change_pct <= improving_below:
        return "improving"
    return "stable"


def pct_change(current: float, previous: float | None) -> float | None:
    if previous is None or previous == 0:
        return None
    return ((current - previous) / previous) * 100.0


async def _latest_two(
    session: AsyncSession, project_id: str, metric_id: str, end: date
) -> tuple[float | None, float | None, date | None]:
    start = months_back(end, 24)
    points = await metric_service.query_series(session, project_id, metric_id, start, end, "month")
    if not points:
        return None, None, None
    latest = points[-1]
    prev = points[-2] if len(points) >= 2 else None
    return float(latest.value), (float(prev.value) if prev else None), latest.period_start


async def compute_derived_metrics(
    session: AsyncSession,
    project: Project,
    end: date | None = None,
) -> dict[str, Any]:
    """Compute bot share, backlog per editor, admin actions per editor for recent months."""
    end = month_start(end or utc_today())
    start = months_back(end, 24)
    written = 0

    async def series_map(metric_id: str) -> dict[date, float]:
        pts = await metric_service.query_series(session, project.id, metric_id, start, end, "month")
        return {p.period_start: float(p.value) for p in pts}

    edits_total = await series_map("edits.total")
    group_bot = await series_map("edits.group_bot")
    name_bot = await series_map("edits.name_bot")
    active = await series_map("editors.active")
    open_total = await series_map("maintenance.open_total")
    admin_total = await series_map("admin.actions_total")

    bot_points: list[SeriesPoint] = []
    for period, total in sorted(edits_total.items()):
        if total <= 0:
            continue
        bots = group_bot.get(period, 0.0) + name_bot.get(period, 0.0)
        bot_points.append(SeriesPoint(period_start=period, value=bots / total))
    if bot_points:
        written += await upsert_series(
            session,
            project.id,
            SeriesResult(metric_id="automation.bot_edit_share", points=bot_points, source="derived"),
            "month",
        )

    backlog_pp: list[SeriesPoint] = []
    for period, open_c in sorted(open_total.items()):
        ae = active.get(period)
        if ae and ae > 0:
            backlog_pp.append(SeriesPoint(period_start=period, value=open_c / ae))
    if backlog_pp:
        written += await upsert_series(
            session,
            project.id,
            SeriesResult(
                metric_id="maintenance.backlog_per_active_editor",
                points=backlog_pp,
                source="derived",
            ),
            "month",
        )

    admin_pp: list[SeriesPoint] = []
    for period, actions in sorted(admin_total.items()):
        ae = active.get(period)
        if ae and ae > 0:
            admin_pp.append(SeriesPoint(period_start=period, value=actions / ae))
    if admin_pp:
        written += await upsert_series(
            session,
            project.id,
            SeriesResult(
                metric_id="admin.actions_per_active_editor",
                points=admin_pp,
                source="derived",
            ),
            "month",
        )

    # Revert rate if reverts.count exists
    reverts = await series_map("reverts.count")
    human = await series_map("edits.user")
    rr: list[SeriesPoint] = []
    for period, rc in sorted(reverts.items()):
        hu = human.get(period)
        if hu and hu > 0:
            rr.append(SeriesPoint(period_start=period, value=rc / hu))
    if rr:
        written += await upsert_series(
            session,
            project.id,
            SeriesResult(metric_id="reverts.rate", points=rr, source="derived"),
            "month",
        )

    return {"derived_points_written": written}


async def build_health_signals(
    session: AsyncSession,
    project: Project,
    end: date | None = None,
) -> dict[str, Any]:
    end = month_start(end or utc_today())
    health = project.health_config or {}
    thresholds = health.get("signal_thresholds") or {}
    default_th = thresholds.get("default_mom_pct") or {"attention_above": 15, "improving_below": -5}

    signal_specs = [
        ("editors.active", "capacity", "Active editors (official)", "default_mom_pct"),
        ("editors.highly_active", "capacity", "Highly active editors (official)", "default_mom_pct"),
        ("maintenance.open_total", "maintenance", "Maintenance backlog", "maintenance_backlog_mom_pct"),
        (
            "maintenance.backlog_per_active_editor",
            "maintenance",
            "Backlog per active editor",
            "maintenance_backlog_mom_pct",
        ),
        ("admin.actions_total", "admin", "Administrative actions", "admin_actions_mom_pct"),
        (
            "admin.actions_per_active_editor",
            "admin",
            "Admin actions per active editor",
            "admin_actions_mom_pct",
        ),
        ("admin.protections", "admin", "Page protections", "default_mom_pct"),
        ("admin.deletions", "admin", "Deletions", "default_mom_pct"),
        ("automation.bot_edit_share", "automation", "Bot edit share", "bot_edit_share_mom_pct"),
        ("reverts.rate", "conflict", "Revert rate", "default_mom_pct"),
        ("edits.total", "context", "Total edits (official context)", "default_mom_pct"),
        ("readers.pageviews", "context", "Page views (official context)", "default_mom_pct"),
    ]

    signals = []
    for metric_id, domain, label, th_key in signal_specs:
        th = thresholds.get(th_key) or default_th
        current, previous, period = await _latest_two(session, project.id, metric_id, end)
        change = pct_change(current, previous) if current is not None else None
        if current is None:
            status: SignalStatus = "unavailable"
        else:
            status = classify_mom(
                change,
                attention_above=float(th.get("attention_above", 15)),
                improving_below=float(th.get("improving_below", -5)),
            )
        direction = "flat"
        if change is not None:
            if change > 0.5:
                direction = "up"
            elif change < -0.5:
                direction = "down"
        definition = await metric_service.get_metric_definition(session, metric_id)
        signals.append(
            {
                "id": metric_id,
                "label": label,
                "domain": domain,
                "value": current,
                "previous": previous,
                "period_start": period.isoformat() if period else None,
                "change_pct": round(change, 2) if change is not None else None,
                "direction": direction,
                "status": status,
                "rule": (
                    f"MoM: attention if ≥{th.get('attention_above')}%, "
                    f"improving if ≤{th.get('improving_below')}%"
                ),
                "role": definition.role if definition else None,
                "source": definition.source if definition else None,
                "provenance_notes": definition.provenance_notes if definition else None,
                "unavailable_reason": None
                if current is not None
                else "No stored value for this metric/period. Configure tracks or run collect-health/ingest.",
            }
        )

    context = [s for s in signals if s["domain"] == "context"]
    primary = [s for s in signals if s["domain"] != "context"]

    return {
        "project_id": project.id,
        "period": {"end": end.isoformat(), "interval": "month"},
        "signals": primary,
        "context": context,
        "disclaimer": (
            "These signals describe operational pressures and capacity trends. "
            "They are not a community health grade. Official activity metrics come from "
            "Wikimedia Analytics (Wikistats family) and are shown as context or denominators."
        ),
        "new_editor_health": (health.get("new_editor_health") or {}),
    }
