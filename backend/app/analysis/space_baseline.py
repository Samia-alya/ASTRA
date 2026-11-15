"""Space-adapted baseline (owner: Member 1).

In microgravity a healthy body settles on values that an Earth-calibrated
tool reads as abnormal (e.g. resting core temperature about 1 °C higher).
This module answers one question: "for this indicator, on this flight day,
how far from the pre-flight value is it NORMAL to be?"

The numbers live in config/space_adaptation.json, each with its source.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.config import space_adaptation


@dataclass
class SpaceContext:
    """What the analysis needs to know about the mission and the person."""
    launch_date: datetime | None = None      # tz-aware
    preflight: float | None = None            # this astronaut's pre-flight value
    model_applies: bool = True                # False e.g. for partial gravity


def flight_day(launch_date: datetime, ts: datetime) -> int:
    """Flight day 1 is launch day."""
    return (ts.date() - launch_date.date()).days + 1


def expected_shift(indicator: str, fd: int) -> float:
    """Expected normal change vs pre-flight on flight day `fd` (0 if no model)."""
    model = space_adaptation().get(indicator)
    if not model or fd < 1:
        return 0.0
    ramp = max(int(model.get("ramp_days", 1)), 1)
    return float(model["shift"]) * min(fd, ramp) / ramp


def has_model(indicator: str) -> bool:
    return indicator in space_adaptation()
