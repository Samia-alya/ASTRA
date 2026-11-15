"""Daily measurement routine ("Today's checks").

Every indicator is expected once per CHECK_WINDOW_HOURS. An indicator is "done"
if it has a measurement within that window before `now` (UTC), otherwise "due".

In Earth-independent mode, the critical indicators (`tight`) are expected every
`tight_hours` instead; their items also carry `interval_hours` and `next_due_in_s`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

CHECK_WINDOW_HOURS = 24


def compute_checks(
    latest: dict[str, datetime | None],
    meta: dict[str, dict],
    now: datetime | None = None,
    tight: set[str] | frozenset[str] = frozenset(),
    tight_hours: float = 2,
) -> dict:
    """Build the checks payload.

    latest: indicator key -> timestamp of its latest measurement (aware UTC) or None.
    meta: indicator metadata (config/indicators.json), which defines the order and labels.
    tight: indicators re-measured every `tight_hours` (Earth-independent mode); empty = usual behaviour.
    """
    now = now or datetime.now(timezone.utc)
    items = []
    for key, m in meta.items():
        ts = latest.get(key)
        hours = None if ts is None else round(max((now - ts).total_seconds(), 0) / 3600, 1)
        window = timedelta(hours=tight_hours if key in tight else CHECK_WINDOW_HOURS)
        done = ts is not None and now - ts <= window
        item = {
            "indicator": key,
            "label": m["label"],
            "unit": m["unit"],
            "done": done,
            "last_timestamp": ts.isoformat() if ts else None,
            "hours_since_last": hours,
        }
        if key in tight:
            item["interval_hours"] = tight_hours
            item["next_due_in_s"] = round((ts + window - now).total_seconds()) if done else 0
        items.append(item)
    return {"done_count": sum(i["done"] for i in items), "total": len(items), "items": items}
