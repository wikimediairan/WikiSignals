from app.services.signals import classify_mom, pct_change


def test_classify_mom_thresholds():
    assert classify_mom(20) == "needs_attention"
    assert classify_mom(-10) == "improving"
    assert classify_mom(0) == "stable"
    assert classify_mom(None) == "unavailable"


def test_pct_change():
    assert pct_change(110, 100) == 10.0
    assert pct_change(100, 0) is None
    assert pct_change(100, None) is None
