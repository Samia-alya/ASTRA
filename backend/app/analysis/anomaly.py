"""Health analysis (owner: Member 1).

Two layers:
  1. Deviation from the astronaut's OWN baseline -> can raise "attention".
     These are statistical rules, not medical thresholds.
  2. Documented reference thresholds (config/thresholds.json) -> the only
     rule allowed to raise "critical".
Every flag comes with human-readable reasons.

Timeline used for one indicator (today = last measurement):

   |<------ baseline (reference period) ------>|<-- recent window -->|
   today-BASELINE_END_DAYS-BASELINE_DAYS        today-RECENT_DAYS     today
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

import pandas as pd
from scipy.stats import linregress

from app.config import indicators, thresholds

BASELINE_DAYS = 10   # length of the personal reference period
RECENT_DAYS = 5      # recent window, excluded from the baseline
Z_ATTENTION = 2.5    # statistical choice (≈ 2.5 standard deviations), NOT medical
TREND_P_VALUE = 0.05
MIN_POINTS = 4


@dataclass
class IndicatorStatus:
    indicator: str
    value: float | None
    baseline: float | None
    level: str = "normal"  # "normal" | "attention" | "critical" | "no_data"
    trend: str = "stable"  # "up" | "down" | "stable"
    reasons: list[str] = field(default_factory=list)
    last_timestamp: str | None = None


def _is_watched(direction: str, delta: float) -> bool:
    """Only flag deviations in the direction that matters for this indicator."""
    if direction == "down":
        return delta < 0
    if direction == "up":
        return delta > 0
    return True


def _beyond(value: float, bound: float, below: bool, inclusive: bool) -> bool:
    """True when value is past the bound (strict unless inclusive)."""
    if below:
        return value <= bound if inclusive else value < bound
    return value >= bound if inclusive else value > bound


def analyse(indicator: str, df: pd.DataFrame) -> IndicatorStatus:
    """df: columns [timestamp, value] (timestamps tz-aware), any order."""
    if df.empty:
        return IndicatorStatus(indicator, None, None, level="no_data")

    direction = indicators().get(indicator, {}).get("watch_direction", "both")
    df = df.sort_values("timestamp")
    last = df.iloc[-1]
    now = last["timestamp"]
    status = IndicatorStatus(
        indicator=indicator,
        value=float(last["value"]),
        baseline=None,
        last_timestamp=now.isoformat(),
    )

    recent_start = now - timedelta(days=RECENT_DAYS)
    baseline_df = df[(df["timestamp"] <= recent_start)
                     & (df["timestamp"] > recent_start - timedelta(days=BASELINE_DAYS))]
    recent_df = df[df["timestamp"] > recent_start]

    # --- Layer 1a: today vs personal baseline ---------------------------
    if len(baseline_df) >= MIN_POINTS:
        mean, std = baseline_df["value"].mean(), baseline_df["value"].std()
        status.baseline = round(float(mean), 2)
        delta = status.value - mean
        if std and std > 0:
            z = delta / std
        else:
            # Perfectly constant baseline (common on a 1-5 scale): any change is unusual.
            z = 0.0 if delta == 0 else float("inf") if delta > 0 else float("-inf")
        if abs(z) >= Z_ATTENTION and _is_watched(direction, z):
            status.level = "attention"
            where = "above" if z > 0 else "below"
            status.reasons.append(
                f"Current value {status.value:g} is well {where} your personal baseline ({mean:.1f})."
            )

    # --- Layer 1b: sustained trend over the recent window ---------------
    if len(recent_df) >= MIN_POINTS:
        x = (recent_df["timestamp"] - recent_df["timestamp"].min()).dt.total_seconds() / 86400
        reg = linregress(x, recent_df["value"])
        if reg.pvalue < TREND_P_VALUE:
            status.trend = "up" if reg.slope > 0 else "down"
            if _is_watched(direction, reg.slope):
                if status.level == "normal":
                    status.level = "attention"
                sens = "Rising" if reg.slope > 0 else "Falling"
                status.reasons.append(
                    f"{sens} trend over {RECENT_DAYS} days ({reg.slope:+.2f} per day)."
                )

    # --- Layer 2: documented thresholds (only source of "critical") -----
    t = thresholds().get(indicator, {})
    low, high, src = t.get("critical_low"), t.get("critical_high"), t.get("source")
    if low is not None and _beyond(status.value, low, below=True, inclusive=t.get("critical_low_inclusive", False)):
        status.level = "critical"
        status.reasons.append(f"Below the reference threshold of {low:g} ({src}).")
    if high is not None and _beyond(status.value, high, below=False, inclusive=t.get("critical_high_inclusive", False)):
        status.level = "critical"
        status.reasons.append(f"Above the reference threshold of {high:g} ({src}).")

    if status.level == "normal":
        status.reasons.append("No unusual change detected.")
    return status
