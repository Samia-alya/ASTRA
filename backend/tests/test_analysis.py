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


def test_heart_rate_above_normal_range_is_attention_not_critical():
    # 101 bpm at rest is above the AHA normal resting range (tachycardia): Watch, not an emergency.
    st = analyse("heart_rate", series(STABLE_HR[:-1] + [101]))
    assert st.level == "attention"
    assert "Above the normal resting range of 100 bpm (American Heart Association)." in st.reasons
    # Heart rate has no critical bound at all.
    assert analyse("heart_rate", series(STABLE_HR[:-1] + [180])).level == "attention"


def test_fever_bound_is_inclusive():
    temps = [36.7] * 14
    assert analyse("temperature", series(temps + [38.0])).level == "critical"
    assert analyse("temperature", series([36.7, 36.8] * 7 + [37.2])).level != "critical"


def test_low_blood_pressure_is_attention_and_strict():
    # NHLBI: below 90/60 is low blood pressure, often harmless without symptoms -> Watch.
    stable = [118, 117, 119, 118, 116, 118, 117, 119, 118, 117, 118, 119, 117, 118]
    at_bound = analyse("bp_systolic", series(stable + [90]))
    assert not any("NHLBI" in r for r in at_bound.reasons)  # strict: 90 itself is not "below 90"
    low = analyse("bp_systolic", series(stable + [89]))
    assert low.level == "attention"
    assert "Below 90 mmHg, defined as low blood pressure (NHLBI)." in low.reasons


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


def test_hypertensive_crisis_is_critical():
    stable = [118, 117, 119, 118, 116, 118, 117, 119, 118, 117, 118, 119, 117, 118]
    st = analyse("bp_systolic", series(stable + [181]))
    assert st.level == "critical"
    assert "Above 180 mmHg, the hypertensive crisis level (American Heart Association)." in st.reasons
    dia = [76, 75, 77, 76, 74, 76, 75, 77, 76, 75, 76, 77, 75, 76]
    assert analyse("bp_diastolic", series(dia + [121])).level == "critical"
    assert analyse("bp_diastolic", series(dia + [59])).level == "attention"


def test_glucose_high_is_attention_low_is_critical():
    stable = [92, 91, 93, 92, 90, 92, 91, 93, 92, 91, 92, 93, 91, 92]
    high = analyse("glucose", series(stable + [250]))
    assert high.level == "attention"
    assert any("check for ketones" in r and "American Diabetes Association" in r for r in high.reasons)
    low = analyse("glucose", series(stable + [53]))
    assert low.level == "critical"
    assert any("level 2" in r and "ADA / EASD" in r for r in low.reasons)


def test_attention_bound_never_lowers_critical():
    # A value beyond a critical bound stays critical whatever attention bounds also say.
    temps = [36.7] * 14
    st = analyse("temperature", series(temps + [38.0]))
    assert st.level == "critical"
    assert "Above the reference threshold of 38 (CDC)." in st.reasons


def test_heart_rate_has_only_a_watch_bound():
    from app.config import thresholds
    t = thresholds()["heart_rate"]
    assert t.get("attention_high") == 100
    assert t.get("critical_low") is None and t.get("critical_high") is None
