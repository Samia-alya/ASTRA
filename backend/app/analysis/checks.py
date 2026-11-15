"""Daily measurement routine ("Today's checks").

Every indicator is expected once per CHECK_WINDOW_HOURS. An indicator is "done"
if it has a measurement within that window before `now` (UTC), otherwise "due".
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

CHECK_WINDOW_HOURS = 24


def compute_checks(
    latest: dict[str, datetime | None],
    meta: dict[str, dict],
    now: datetime | None = None,
) -> dict:
    """Build the checks payload.

    latest: indicator key -> timestamp of its latest measurement (aware UTC) or None.
    meta: indicator metadata (config/indicators.json), which defines the order and labels.
    """
    now = now or datetime.now(timezone.utc)
    window = timedelta(hours=CHECK_WINDOW_HOURS)
    items = []
    for key, m in meta.items():
        ts = latest.get(key)
        hours = None if ts is None else round(max((now - ts).total_seconds(), 0) / 3600, 1)
        items.append({
            "indicator": key,
            "label": m["label"],
            "unit": m["unit"],
            "done": ts is not None and now - ts <= window,
            "last_timestamp": ts.isoformat() if ts else None,
            "hours_since_last": hours,
        })
    return {"done_count": sum(i["done"] for i in items), "total": len(items), "items": items}
