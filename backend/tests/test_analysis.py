"""Run from backend/:  python -m pytest -q"""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from app.analysis.anomaly import analyse, earth_reference_flags
from app.analysis.correlation import evaluate, readiness
from app.analysis.space_baseline import SpaceContext, expected_shift

LAUNCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


def series(indicator: str, preflight: float, days: int, noise: float, tail=(), seed: int = 0):
    """Daily values that follow the expected in-flight curve, then `tail`."""
    rng = np.random.default_rng(seed)
    rows = []
    for fd in range(1, days + 1):
        k = fd - (days - len(tail)) - 1
        v = tail[k] if 0 <= k < len(tail) else preflight + expected_shift(indicator, fd) + rng.normal(0, noise)
        rows.append({"timestamp": pd.Timestamp(LAUNCH + timedelta(days=fd - 1)), "value": float(v)})
    return pd.DataFrame(rows)


def test_expected_shift_ramps_then_plateaus():
    assert expected_shift("temperature", 0) == 0
    assert 0 < expected_shift("temperature", 30) < 1.0
    assert expected_shift("temperature", 75) == 1.0
    assert expected_shift("temperature", 200) == 1.0
    assert expected_shift("heart_rate", 100) == 0  # no sourced model -> no adjustment


def test_adapted_temperature_is_normal_in_space_but_flagged_on_earth():
    df = series("temperature", 37.1, 100, 0.05, seed=1)
    ctx = SpaceContext(launch_date=LAUNCH, preflight=37.1)
    assert analyse("temperature", df, ctx, mode="space").level == "normal"
    assert analyse("temperature", df, ctx, mode="earth").level == "attention"  # "fever" >= 38
    assert earth_reference_flags("temperature", df, ctx) > 10


def test_temperature_above_adapted_baseline_is_flagged():
    df = series("temperature", 37.0, 145, 0.05, tail=(38.2, 38.3, 38.4, 38.5))
    st = analyse("temperature", df, SpaceContext(launch_date=LAUNCH, preflight=37.0))
    assert st.level == "attention" and st.space_adjusted


def test_critical_limit_is_never_shifted():
    df = series("temperature", 37.0, 145, 0.05, tail=(40.2,))
    st = analyse("temperature", df, SpaceContext(launch_date=LAUNCH, preflight=37.0))
    assert st.level == "critical"


def test_model_not_applied_in_partial_gravity():
    df = series("temperature", 37.1, 100, 0.05)
    ctx = SpaceContext(launch_date=LAUNCH, preflight=37.1, model_applies=False)
    assert not analyse("temperature", df, ctx).space_adjusted


def test_masked_fatigue_blocks_critical_operations():
    ctx = SpaceContext(launch_date=LAUNCH)
    frames = {
        "sleep_hours": series("sleep_hours", 6.8, 60, 0.2, tail=(5.5, 5.3, 5.1)),
        "pvt_lapses": series("pvt_lapses", 1.0, 60, 0.4, tail=(3, 4, 5)),
        "pvt_mean_rt": series("pvt_mean_rt", 224, 60, 5, tail=(250, 260, 268)),
        "alertness": series("alertness", 7.0, 60, 0.3, tail=(7, 7, 7)),
    }
    statuses = {k: analyse(k, v, ctx) for k, v in frames.items()}
    alerts = evaluate(statuses, frames)
    assert [a["rule"] for a in alerts] == ["masked_fatigue"]
    assert readiness(statuses, alerts)["status"] == "NO_GO"


def test_no_alert_when_astronaut_reports_feeling_tired():
    ctx = SpaceContext(launch_date=LAUNCH)
    frames = {
        "sleep_hours": series("sleep_hours", 6.8, 60, 0.2, tail=(5.5, 5.3, 5.1)),
        "pvt_lapses": series("pvt_lapses", 1.0, 60, 0.4, tail=(3, 4, 5)),
        "alertness": series("alertness", 7.0, 60, 0.3, tail=(5, 4, 3)),  # honest self-report
    }
    statuses = {k: analyse(k, v, ctx) for k, v in frames.items()}
    assert "masked_fatigue" not in [a["rule"] for a in evaluate(statuses, frames)]
