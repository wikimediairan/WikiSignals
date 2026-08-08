from datetime import date

import pytest

from app.timeutil import (
    add_interval,
    iso_week_start,
    iter_periods,
    month_start,
    months_back,
    period_start_for,
    quarter_start,
)


def test_month_start_and_boundaries():
    assert month_start(date(2024, 3, 15)) == date(2024, 3, 1)
    assert period_start_for(date(2024, 2, 29), "month") == date(2024, 2, 1)


def test_iso_week_monday():
    # 2024-01-03 is Wednesday
    assert iso_week_start(date(2024, 1, 3)) == date(2024, 1, 1)


def test_quarter_start():
    assert quarter_start(date(2024, 5, 10)) == date(2024, 4, 1)
    assert quarter_start(date(2024, 1, 1)) == date(2024, 1, 1)


def test_add_interval_month_year_wrap():
    assert add_interval(date(2023, 11, 1), "month", 2) == date(2024, 1, 1)
    assert add_interval(date(2024, 1, 1), "year", 1) == date(2025, 1, 1)


def test_iter_periods_month():
    periods = iter_periods(date(2024, 1, 15), date(2024, 3, 20), "month")
    assert periods == [date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1)]


def test_months_back():
    assert months_back(date(2024, 6, 1), 6) == date(2023, 12, 1)


@pytest.mark.parametrize(
    "d,interval,expected",
    [
        (date(2024, 12, 31), "year", date(2024, 1, 1)),
        (date(2020, 2, 29), "month", date(2020, 2, 1)),
        (date(2024, 1, 1), "day", date(2024, 1, 1)),
    ],
)
def test_period_start_param(d, interval, expected):
    assert period_start_for(d, interval) == expected
