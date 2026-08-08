from datetime import date

from app.providers.aqs import ACTIVITY_LEVELS, EDITOR_TYPES_EDITS, _items_from_aqs, _points_from_items, _sum_series
from app.providers.base import SeriesPoint, SeriesResult


def test_editor_type_mapping_has_no_language_hardcode():
    assert "fa" not in str(EDITOR_TYPES_EDITS)
    assert "all-editor-types" in EDITOR_TYPES_EDITS


def test_parse_nested_results():
    payload = {
        "items": [
            {
                "results": [
                    {"timestamp": "2024010100", "edits": 10},
                    {"timestamp": "2024020100", "edits": 20},
                ]
            }
        ]
    }
    items = _items_from_aqs(payload)
    points = _points_from_items(items, value_keys=("edits",))
    assert points == [
        SeriesPoint(period_start=date(2024, 1, 1), value=10.0),
        SeriesPoint(period_start=date(2024, 2, 1), value=20.0),
    ]


def test_range_end_single_month():
    from datetime import date

    from app.providers.aqs import AQSProvider

    start = date(2024, 1, 1)
    assert AQSProvider._range_end(start, start, "monthly") == date(2024, 2, 1)
    assert AQSProvider._range_end(start, date(2024, 6, 1), "monthly") == date(2024, 6, 1)


def test_active_editors_sum():
    a = SeriesResult(
        metric_id="editors.activity_5_24",
        points=[SeriesPoint(date(2024, 1, 1), 50)],
        source="aqs",
    )
    b = SeriesResult(
        metric_id="editors.activity_25_99",
        points=[SeriesPoint(date(2024, 1, 1), 20)],
        source="aqs",
    )
    c = SeriesResult(
        metric_id="editors.highly_active",
        points=[SeriesPoint(date(2024, 1, 1), 5)],
        source="aqs",
    )
    active = _sum_series("editors.active", [a, b, c])
    assert active.points[0].value == 75.0
    assert set(ACTIVITY_LEVELS.values()) >= {
        "editors.activity_5_24",
        "editors.highly_active",
    }
