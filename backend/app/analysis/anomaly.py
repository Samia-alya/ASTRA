"""Health analysis (owner: Member 1).

Three layers, each with human-readable reasons:
  1. Deviation from the astronaut's OWN baseline -> can raise "attention".
     Statistical rules, not medical thresholds: (a) today is >= 2.5 standard
     deviations from the personal baseline; (b) a significant trend over the
     recent window whose total change exceeds two baseline standard deviations.
  2. Earth clinical reference values (config/thresholds.json, reference_*)
     -> can raise "attention".
  3. Documented absolute limits (config/thresholds.json, critical_*)
     -> the only rule allowed to raise "critical".

Space mode (default) vs Earth mode
----------------------------------
For indicators that have a sourced adaptation model (space_adaptation.json),
space mode first removes the EXPECTED in-flight change from every value, so
layers 1-2 only react to what the normal adaptation does not explain.
Layer 3 is never adjusted: absolute limits stay absolute.
Earth mode runs the same rules with no adjustment; it shows what a tool
calibrated for Earth would have said.

Timeline used for one indicator (today = last measurement):

   |<------ baseline (reference period) ------>|<-- recent window -->|
   today-BASELINE_END_DAYS-BASELINE_DAYS        today-RECENT_DAYS     today
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

import pandas as pd
from scipy.stats import linregress

from app.analysis.space_baseline import SpaceContext, expected_shift, flight_day, has_model
from app.config import indicators, thresholds

BASELINE_DAYS = 10   # length of the personal reference period
RECENT_DAYS = 5      # recent window, excluded from the baseline
Z_ATTENTION = 2.5    # statistical choice (≈ 2.5 standard deviations), NOT medical
TREND_P_VALUE = 0.05
TREND_MIN_SD = 2.0   # statistical choice: minimum size of a trend, in baseline SDs
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
    # --- space-adapted context (None when unknown) ---
    flight_day: int | None = None
    preflight: float | None = None       # pre-flight value on Earth
    expected: float | None = None        # pre-flight + expected in-flight change today
    band_low: float | None = None        # personal normal band today
    band_high: float | None = None
    deviation_pct: float | None = None   # today vs personal baseline, in %
    space_adjusted: bool = False         # True when an adaptation model was applied
    slope_per_day: float | None = None   # change per day over the recent window (expected change removed)


def _is_watched(direction: str, delta: float) -> bool:
    """Only flag deviations in the direction that matters for this indicator."""
    if direction == "down":
        return delta < 0
    if direction == "up":
        return delta > 0
    return True


def _shifts(indicator: str, df: pd.DataFrame, ctx: SpaceContext | None, mode: str) -> pd.Series:
    """Expected normal in-flight change for each row (all zeros in Earth mode)."""
    if mode != "space" or ctx is None or ctx.launch_date is None \
            or not ctx.model_applies or not has_model(indicator):
        return pd.Series(0.0, index=df.index)
    return df["timestamp"].map(lambda ts: expected_shift(indicator, flight_day(ctx.launch_date, ts)))


def analyse(indicator: str, df: pd.DataFrame, ctx: SpaceContext | None = None,
            mode: str = "space") -> IndicatorStatus:
    """df: columns [timestamp, value] (timestamps tz-aware), any order."""
    if df.empty:
        return IndicatorStatus(indicator, None, None, level="no_data")

    meta = indicators().get(indicator, {})
    direction = meta.get("watch_direction", "both")
    unit = meta.get("unit", "")
    df = df.sort_values("timestamp").reset_index(drop=True)
    shift = _shifts(indicator, df, ctx, mode)
    adjusted = bool((shift != 0).any())
    # "adj" = value with the expected adaptation removed.
    df = df.assign(adj=df["value"] - shift)
    last = df.iloc[-1]
    now = last["timestamp"]
    shift_now = float(shift.iloc[-1])
    status = IndicatorStatus(
        indicator=indicator,
        value=float(last["value"]),
        baseline=None,
        last_timestamp=now.isoformat(),
        space_adjusted=adjusted,
    )
    if ctx is not None:
        status.preflight = ctx.preflight
        if ctx.launch_date is not None:
            status.flight_day = flight_day(ctx.launch_date, now)
        if ctx.preflight is not None:
            status.expected = round(ctx.preflight + shift_now, 2)

    recent_start = now - timedelta(days=RECENT_DAYS)
    baseline_df = df[(df["timestamp"] <= recent_start)
                     & (df["timestamp"] > recent_start - timedelta(days=BASELINE_DAYS))]
    recent_df = df[df["timestamp"] > recent_start]
    what = "space-adapted baseline" if adjusted else "personal baseline"

    # --- Layer 1a: today vs personal baseline ---------------------------
    base_std: float | None = None
    if len(baseline_df) >= MIN_POINTS:
        mean, std = float(baseline_df["adj"].mean()), float(baseline_df["adj"].std())
        today_baseline = mean + shift_now
        status.baseline = round(today_baseline, 2)
        if today_baseline:
            status.deviation_pct = round(100 * (status.value - today_baseline) / abs(today_baseline), 1)
        if std and std > 0:
            base_std = std
            status.band_low = round(today_baseline - Z_ATTENTION * std, 2)
            status.band_high = round(today_baseline + Z_ATTENTION * std, 2)
            z = (float(last["adj"]) - mean) / std
            if abs(z) >= Z_ATTENTION and _is_watched(direction, z):
                status.level = "attention"
                where = "well above" if z > 0 else "well below"
                extra = " The normal in-flight change is already accounted for." if adjusted else ""
                status.reasons.append(
                    f"Current value {status.value:g} {unit} is {where} your {what} "
                    f"({today_baseline:.1f} {unit}).{extra}"
                )

    # --- Layer 1b: sustained trend over the recent window ---------------
    if len(recent_df) >= MIN_POINTS:
        x = (recent_df["timestamp"] - recent_df["timestamp"].min()).dt.total_seconds() / 86400
        if x.nunique() > 1 and recent_df["adj"].nunique() > 1:
            reg = linregress(x, recent_df["adj"])
            status.slope_per_day = round(float(reg.slope), 3)
            # Significant AND large enough to matter: the change over the window must
            # exceed TREND_MIN_SD standard deviations of the personal baseline (when
            # known). Without this guard, 5 noisy points flag a trend far too often.
            big_enough = base_std is None or abs(reg.slope) * RECENT_DAYS >= TREND_MIN_SD * base_std
            if reg.pvalue < TREND_P_VALUE and big_enough:
                status.trend = "up" if reg.slope > 0 else "down"
                if _is_watched(direction, reg.slope):
                    if status.level == "normal":
                        status.level = "attention"
                    sens = "Rising" if reg.slope > 0 else "Falling"
                    beyond = " beyond the expected in-flight change" if adjusted else ""
                    status.reasons.append(
                        f"{sens} trend over {RECENT_DAYS} days ({reg.slope:+.2f} {unit} per day){beyond}."
                    )

    # --- Layer 2: Earth clinical reference values -> "attention" --------
    t = thresholds().get(indicator, {})
    src = t.get("source")
    ref_low, ref_high = t.get("reference_low"), t.get("reference_high")
    adj_note = f" (Earth reference {{ref:g}} adjusted by {shift_now:+.1f} for expected in-flight change)" \
        if adjusted else ""
    if ref_low is not None and status.value < ref_low + shift_now:
        if status.level == "normal":
            status.level = "attention"
        status.reasons.append(
            f"Below the reference value {ref_low + shift_now:g} {unit}"
            f"{adj_note.format(ref=ref_low)}. Source: {src}"
        )
    if ref_high is not None and status.value >= ref_high + shift_now:
        if status.level == "normal":
            status.level = "attention"
        status.reasons.append(
            f"At or above the reference value {ref_high + shift_now:g} {unit}"
            f"{adj_note.format(ref=ref_high)}. Source: {src}"
        )

    # --- Layer 3: documented absolute limits (only source of "critical") -
    low, high = t.get("critical_low"), t.get("critical_high")
    crit_src = t.get("critical_source", src)
    if low is not None and status.value < low:
        status.level = "critical"
        status.reasons.append(f"Below the critical limit {low:g} {unit}. Source: {crit_src}")
    if high is not None and status.value > high:
        status.level = "critical"
        status.reasons.append(f"Above the critical limit {high:g} {unit}. Source: {crit_src}")

    if status.level == "normal":
        if adjusted and status.expected is not None and status.preflight is not None:
            status.reasons.append(
                f"Within your space-adapted range. Expected today: about {status.expected:g} {unit} "
                f"(pre-flight {status.preflight:g} {unit})."
            )
        else:
            status.reasons.append("No unusual change detected.")
    return status


def earth_reference_flags(indicator: str, df: pd.DataFrame, ctx: SpaceContext | None) -> int:
    """How many past measurements an Earth reference value would have flagged
    although they sit inside the expected in-flight adaptation."""
    if df.empty or ctx is None or not has_model(indicator):
        return 0
    t = thresholds().get(indicator, {})
    ref_low, ref_high = t.get("reference_low"), t.get("reference_high")
    if ref_low is None and ref_high is None:
        return 0
    shift = _shifts(indicator, df, ctx, "space")
    v = df["value"]
    earth = pd.Series(False, index=df.index)
    space = pd.Series(False, index=df.index)
    if ref_low is not None:
        earth |= v < ref_low
        space |= v < ref_low + shift
    if ref_high is not None:
        earth |= v >= ref_high
        space |= v >= ref_high + shift
    return int((earth & ~space).sum())
