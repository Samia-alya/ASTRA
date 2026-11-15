"""Input validation for manually entered measurements.

IMPORTANT: the limits used here ("input" in config/indicators.json) are
PLAUSIBILITY LIMITS for data entry. They catch typos and physically impossible
values. They are NOT medical thresholds and must never be used by the analysis
(app/analysis/), whose levels come only from the personal baseline and the
documented thresholds in config/thresholds.json.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

STEP_TOLERANCE = 1e-6
MAX_FUTURE = timedelta(minutes=5)


def _num(x: float) -> str:
    """Limits are shown as written in indicators.json: 20, 30.0, 0.25."""
    return str(x)


def validate_value(meta: dict, value: float) -> str | None:
    """Return an error message, or None when the value is plausible for this indicator."""
    label = meta["label"]
    limits = meta.get("input")
    if not math.isfinite(value):
        return f"{label} must be a finite number."
    if not limits:
        return None
    lo, hi, step = limits["min"], limits["max"], limits["step"]
    # "/5" reads badly after a number ("between 1 and 5 /5"), so it is left out.
    unit = "" if meta["unit"].startswith("/") else f" {meta['unit']}"
    if not lo - STEP_TOLERANCE <= value <= hi + STEP_TOLERANCE:
        return f"{label} must be between {_num(lo)} and {_num(hi)}{unit}."
    k = (value - lo) / step
    if abs(k - round(k)) > STEP_TOLERANCE * max(1.0, abs(k)):
        if step == 1:
            return f"{label} must be a whole number."
        return f"{label} must be in steps of {_num(step)}{unit}."
    return None


def validate_timestamp(ts: datetime | None, now: datetime | None = None) -> str | None:
    """Reject timestamps more than MAX_FUTURE ahead of now. `ts` must be timezone-aware."""
    if ts is None:
        return None
    now = now or datetime.now(timezone.utc)
    if ts - now > MAX_FUTURE:
        return "The measurement time cannot be in the future."
    return None
