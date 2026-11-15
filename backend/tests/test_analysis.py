"""Tests for the health analysis rules (app/analysis/anomaly.py).

Run from backend/:  python -m pytest -q
"""
from datetime import datetime, timedelta, timezone

import pandas as pd

from app.analysis.anomaly import analyse

NOW = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)


def series(values: list[float]) -> pd.DataFrame:
    """One value per day, the last one = NOW."""
    n = len(values)
    return pd.DataFrame({
        "timestamp": [NOW - timedelta(days=n - 1 - i) for i in range(n)],
        "value": values,
    })


STABLE_HR = [64, 65, 63, 64, 66, 63, 64, 65, 64, 63, 64, 65, 64, 63, 64]


def test_no_data():
    assert analyse("heart_rate", pd.DataFrame()).level == "no_data"


def test_stable_values_are_normal():
    st = analyse("heart_rate", series(STABLE_HR))
    assert st.level == "normal"
    assert st.baseline is not None
    assert st.reasons == ["No unusual change detected."]


def test_jump_from_personal_baseline_is_attention():
    st = analyse("heart_rate", series(STABLE_HR[:-1] + [80]))
    assert st.level == "attention"
    assert any("above your personal baseline" in r for r in st.reasons)


def test_sustained_trend_is_attention():
    values = [64] * 10 + [65, 67, 69, 71, 73]
    st = analyse("heart_rate", series(values))
    assert st.trend == "up"
    assert st.level == "attention"


def test_watch_direction_ignores_good_changes():
    # Sleep is watched only when it goes DOWN: more sleep must not raise an alert.
    sleep = [7.0, 6.9, 7.1, 7.0, 6.8, 7.0, 6.9, 7.1, 7.0, 6.9, 7.0, 7.1, 7.0, 6.9, 9.5]
    assert analyse("sleep_hours", series(sleep)).level == "normal"


def test_less_sleep_is_flagged():
    sleep = [7.0, 6.9, 7.1, 7.0, 6.8, 7.0, 6.9, 7.1, 7.0, 6.9, 7.0, 7.1, 7.0, 6.9, 4.0]
    assert analyse("sleep_hours", series(sleep)).level == "attention"


def test_documented_threshold_is_critical():
    # 101 bpm at rest is above the AHA 100 bpm bound -> critical, with the source named.
    st = analyse("heart_rate", series(STABLE_HR[:-1] + [101]))
    assert st.level == "critical"
    assert any("reference threshold" in r and "American Heart Association" in r for r in st.reasons)


def test_fever_bound_is_inclusive():
    temps = [36.7] * 14
    assert analyse("temperature", series(temps + [38.0])).level == "critical"
    assert analyse("temperature", series([36.7, 36.8] * 7 + [37.2])).level != "critical"


def test_low_bound_is_strict():
    stable = [118, 117, 119, 118, 116, 118, 117, 119, 118, 117, 118, 119, 117, 118]
    assert analyse("bp_systolic", series(stable + [90])).level != "critical"
    assert analyse("bp_systolic", series(stable + [89])).level == "critical"


def test_mood_never_critical():
    # No documented threshold for a self-reported scale.
    st = analyse("mood", series([4] * 14 + [1]))
    assert st.level == "attention"


def test_reason_baseline_uses_display_rounding():
    """The reason shows the baseline with the same rounding as the UI (whole mmHg here, not 117.9)."""
    from app.config import display_value
    assert display_value("bp_systolic", 117.9) == "118"
    assert display_value("temperature", 36.68) == "36.7"
    assert display_value("sleep_hours", 6.25) == "6.3"  # half-up, like JavaScript toFixed
    st = analyse("bp_systolic", series([118, 117, 119, 118, 117, 118, 118, 117, 119, 118, 117, 118, 118, 118, 150]))
    reason = next(r for r in st.reasons if "baseline" in r)
    assert "(118)" in reason and "." not in reason.split("baseline")[1].rstrip(".")
