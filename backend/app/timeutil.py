"""UTC period helpers for aggregation boundaries."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal

Interval = Literal["day", "week", "month", "quarter", "year"]


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def parse_date(value: str | date) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value)[:10])


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def next_month_start(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def quarter_start(d: date) -> date:
    q_month = ((d.month - 1) // 3) * 3 + 1
    return date(d.year, q_month, 1)


def year_start(d: date) -> date:
    return date(d.year, 1, 1)


def iso_week_start(d: date) -> date:
    """Monday of the ISO week containing d (UTC calendar date)."""
    return d - timedelta(days=d.weekday())


def period_start_for(d: date, interval: Interval) -> date:
    if interval == "day":
        return d
    if interval == "week":
        return iso_week_start(d)
    if interval == "month":
        return month_start(d)
    if interval == "quarter":
        return quarter_start(d)
    if interval == "year":
        return year_start(d)
    raise ValueError(f"Unsupported interval: {interval}")


def add_interval(d: date, interval: Interval, steps: int = 1) -> date:
    if steps == 0:
        return d
    if interval == "day":
        return d + timedelta(days=steps)
    if interval == "week":
        return d + timedelta(weeks=steps)
    if interval == "month":
        y = d.year
        m = d.month + steps
        while m > 12:
            m -= 12
            y += 1
        while m < 1:
            m += 12
            y -= 1
        return date(y, m, 1)
    if interval == "quarter":
        return add_interval(d, "month", steps * 3)
    if interval == "year":
        return date(d.year + steps, d.month, d.day)
    raise ValueError(f"Unsupported interval: {interval}")


def iter_periods(start: date, end: date, interval: Interval) -> list[date]:
    """Inclusive period starts from start..end (normalized to period starts)."""
    cur = period_start_for(start, interval)
    last = period_start_for(end, interval)
    out: list[date] = []
    while cur <= last:
        out.append(cur)
        cur = add_interval(cur, interval, 1)
    return out


def aqs_date_token(d: date, granularity: str) -> str:
    """Format dates for AQS path segments."""
    if granularity == "daily":
        return d.strftime("%Y%m%d")
    if granularity == "monthly":
        return d.strftime("%Y%m%d")
    # pageviews sometimes wants hour suffix
    return d.strftime("%Y%m%d")


def aqs_pageviews_token(d: date) -> str:
    return d.strftime("%Y%m%d00")


def months_back(from_date: date | None = None, months: int = 24) -> date:
    base = from_date or utc_today()
    y = base.year
    m = base.month - months
    while m <= 0:
        m += 12
        y -= 1
    return date(y, m, 1)
