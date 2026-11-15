"""Device readings endpoint. Every device in this app is SIMULATED (see config/devices.json)."""
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session

from app.config import devices, indicators
from app.database import get_session
from app.models import Device, Measurement, ReadingsIn
from app.routers.astronauts import _as_utc
from app.validation import validate_timestamp, validate_value

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/{device_id}/readings", status_code=201)
def post_readings(
    device_id: int,
    payload: ReadingsIn,
    x_device_token: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
):
    """Store a batch of readings (1–100) sent by a device.

    The whole batch is rejected (422) if any reading is not supported by this device kind
    or fails the plausibility validation, so a device never half-uploads a batch.
    """
    device = session.get(Device, device_id)
    if device is None:
        raise HTTPException(404, f"Device {device_id} not found")
    if not x_device_token or not secrets.compare_digest(x_device_token, device.token):
        raise HTTPException(401, "Missing or invalid X-Device-Token.")

    supported = devices().get(device.kind, {}).get("indicators", [])
    meta = indicators()
    now = datetime.now(timezone.utc)
    rows = []
    for i, r in enumerate(payload.readings, start=1):
        if r.indicator not in supported:
            raise HTTPException(
                422, f"Reading {i}: a {device.kind} device cannot send '{r.indicator}' "
                f"(supported: {', '.join(supported)})."
            )
        ts = _as_utc(r.timestamp) if r.timestamp else None
        # Plausibility limits for data entry only, not medical thresholds (see app/validation.py).
        problem = validate_value(meta[r.indicator], r.value) or validate_timestamp(ts, now)
        if problem:
            raise HTTPException(422, f"Reading {i}: {problem}")
        rows.append(Measurement(
            astronaut_id=device.astronaut_id, indicator=r.indicator, value=r.value,
            timestamp=ts or now, source="device", device_id=device.id,
        ))

    session.add_all(rows)
    device.last_seen = now
    session.add(device)
    session.commit()
    return {"stored": len(rows), "device_id": device.id, "last_seen": now.isoformat()}
