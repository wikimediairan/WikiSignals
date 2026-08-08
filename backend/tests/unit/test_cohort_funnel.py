"""Cohort funnel pure-logic tests using synthetic timelines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class UserEvent:
    user_id: int
    registered: date
    edit_days: list[date]


def funnel_for_cohort(users: list[UserEvent], cohort_month: date) -> dict[str, int]:
    """Reference implementation for retention stages."""
    cohort = [u for u in users if u.registered.year == cohort_month.year and u.registered.month == cohort_month.month]
    accounts = len(cohort)
    first = sum(1 for u in cohort if u.edit_days)
    second = sum(1 for u in cohort if len(u.edit_days) >= 2)

    def active_within(days: int) -> int:
        n = 0
        for u in cohort:
            for ed in u.edit_days:
                if timedelta(0) <= (ed - u.registered) <= timedelta(days=days):
                    n += 1
                    break
        return n

    return {
        "funnel.accounts": accounts,
        "funnel.first_edit": first,
        "funnel.second_edit": second,
        "funnel.active_7d": active_within(7),
        "funnel.active_30d": active_within(30),
        "funnel.active_90d": active_within(90),
        "funnel.active_180d": active_within(180),
    }


def test_funnel_stages():
    users = [
        UserEvent(1, date(2024, 1, 5), [date(2024, 1, 6), date(2024, 1, 20)]),
        UserEvent(2, date(2024, 1, 10), [date(2024, 2, 1)]),  # first edit after 7d
        UserEvent(3, date(2024, 1, 15), []),  # no edits
        UserEvent(4, date(2024, 2, 1), [date(2024, 2, 2)]),  # other cohort
    ]
    result = funnel_for_cohort(users, date(2024, 1, 1))
    assert result["funnel.accounts"] == 3
    assert result["funnel.first_edit"] == 2
    assert result["funnel.second_edit"] == 1
    assert result["funnel.active_7d"] == 1
    assert result["funnel.active_30d"] == 2
