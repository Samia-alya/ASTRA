"""Earth-independent mode (inspired by NASA's Earth-Independent Medical Operations concept).

The same Critical alert gets a different response depending on the distance to Earth:

- Near Earth (station, Moon): contact the flight surgeon now.
- Far from Earth (Mars transit): a reply from Earth would come too late, so the app guides the crew
  through onboard monitoring steps while they wait.

Rule (signal physics only): active = overall level is "critical" AND 2 x one_way_delay_s > round_trip_threshold_s.
ground_response_s is only used for earliest_reply_s, never in the rule.
The parameters in config/environments.json are prototype design choices, not NASA rules.

Episodes: only checked steps and reports from the last `episode_window_hours` (24 h) count, so a step
checked during a past alert does not show as already done during a new one.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.config import autonomy_rule, environments


def _minutes(seconds: float) -> str:
    m = seconds / 60
    return f"{m:.0f} min" if m >= 1 else f"{seconds:g} s"


def autonomy_state(overall_level: str, environment: str) -> dict:
    """The `autonomy` block of GET /astronauts/{id}/status."""
    rule = autonomy_rule()
    env = environments().get(environment)
    if env is None:  # unknown environment: assume near Earth, never switch on silently
        delay = 0.0
    else:
        delay = float(env["one_way_delay_s"])
    round_trip = 2 * delay
    earliest = round_trip + rule["ground_response_s"]
    critical = overall_level == "critical"
    active = critical and round_trip > rule["round_trip_threshold_s"]

    if active:
        reason = (
            f"Critical alert. A reply from Earth takes at least {_minutes(earliest)} "
            f"({_minutes(round_trip)} signal round trip + {_minutes(rule['ground_response_s'])} ground response). "
            "Follow the onboard monitoring steps now and send a report to Earth."
        )
    elif critical:
        reason = (
            f"Critical alert. The signal round trip to Earth is only {_minutes(round_trip)}: "
            "contact your flight surgeon now."
        )
    else:
        reason = "No critical alert: Earth-independent mode is not needed."

    return {
        "active": active,
        "one_way_delay_s": delay,
        "earliest_reply_s": earliest,
        "reason": reason,
    }


def episode_start(now: datetime | None = None) -> datetime:
    """Actions and reports older than this belong to a past alert and are ignored."""
    now = now or datetime.now(timezone.utc)
    return now - timedelta(hours=autonomy_rule()["episode_window_hours"])
