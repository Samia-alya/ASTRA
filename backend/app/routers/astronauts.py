"""Astronaut, measurement and status endpoints (owner: Member 2)."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from app.analysis.anomaly import analyse
from app.analysis.checks import compute_checks
from app.config import devices, indicators
from app.database import get_session
from app.models import Astronaut, Device, Measurement, MeasurementCreate, MeasurementRead
from app.validation import validate_timestamp, validate_value

router = APIRouter(prefix="/astronauts", tags=["astronauts"])


def _as_utc(dt: datetime) -> datetime:
    """Naive datetimes are assumed to be UTC."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _get_astronaut(astronaut_id: int, session: Session) -> Astronaut:
    astro = session.get(Astronaut, astronaut_id)
    if not astro:
        raise HTTPException(404, f"Astronaut {astronaut_id} not found")
    return astro


LIVE_WINDOW = timedelta(minutes=2)   # streaming right now
SYNC_WINDOW = timedelta(hours=24)    # e.g. a sleep band that syncs once a day


def device_status(last_seen: datetime | None, now: datetime) -> str:
    """live (< 2 min) | synced (< 24 h) | stale (≥ 24 h) | never"""
    if last_seen is None:
        return "never"
    age = now - last_seen
    return "live" if age < LIVE_WINDOW else "synced" if age < SYNC_WINDOW else "stale"


def device_view(d: Device, now: datetime | None = None, latest: list[dict] | None = None) -> dict:
    """Public view of a device: never includes the token."""
    now = now or datetime.now(timezone.utc)
    seen = _as_utc(d.last_seen) if d.last_seen else None
    return {
        "id": d.id,
        "kind": d.kind,
        "name": d.name,
        "simulated": d.simulated,
        "last_seen": seen.isoformat() if seen else None,
        "status": device_status(seen, now),
        "indicators": devices().get(d.kind, {}).get("indicators", []),
        "latest": latest or [],
    }


def _latest_from_device(d: Device, session: Session) -> list[dict]:
    """Latest reading this device sent for each indicator it supports."""
    meta = indicators()
    out = []
    for key in devices().get(d.kind, {}).get("indicators", []):
        m = session.exec(
            select(Measurement)
            .where(Measurement.device_id == d.id, Measurement.indicator == key)
            .order_by(Measurement.timestamp.desc())
            .limit(1)
        ).first()
        if m:
            out.append({"indicator": key, "label": meta[key]["label"], "unit": meta[key]["unit"],
                        "value": m.value, "timestamp": _as_utc(m.timestamp).isoformat()})
    return out


def _device_names(astronaut_id: int, session: Session) -> dict[int, str]:
    rows = session.exec(select(Device.id, Device.name).where(Device.astronaut_id == astronaut_id)).all()
    return {i: n for i, n in rows}


@router.get("", response_model=list[Astronaut])
def list_astronauts(session: Session = Depends(get_session)):
    return session.exec(select(Astronaut)).all()


@router.get("/{astronaut_id}/devices")
def list_devices(astronaut_id: int, session: Session = Depends(get_session)):
    """Devices paired with this astronaut (all simulated in this demo). Tokens are never returned."""
    _get_astronaut(astronaut_id, session)
    rows = session.exec(select(Device).where(Device.astronaut_id == astronaut_id).order_by(Device.id)).all()
    now = datetime.now(timezone.utc)
    return [device_view(d, now, _latest_from_device(d, session)) for d in rows]


@router.get("/{astronaut_id}/measurements", response_model=list[MeasurementRead])
def list_measurements(
    astronaut_id: int,
    indicator: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    session: Session = Depends(get_session),
):
    _get_astronaut(astronaut_id, session)
    q = select(Measurement).where(Measurement.astronaut_id == astronaut_id)
    if indicator:
        q = q.where(Measurement.indicator == indicator)
    if start:
        q = q.where(Measurement.timestamp >= _as_utc(start))
    if end:
        q = q.where(Measurement.timestamp <= _as_utc(end))
    names = _device_names(astronaut_id, session)
    return [
        MeasurementRead(**m.model_dump(), device_name=names.get(m.device_id) if m.device_id else None)
        for m in session.exec(q.order_by(Measurement.timestamp)).all()
    ]


@router.post("/{astronaut_id}/measurements", response_model=Measurement, status_code=201)
def add_measurement(
    astronaut_id: int, payload: MeasurementCreate, session: Session = Depends(get_session)
):
    _get_astronaut(astronaut_id, session)
    meta = indicators().get(payload.indicator)
    if meta is None:
        raise HTTPException(422, f"Unknown indicator '{payload.indicator}'")
    # Plausibility limits for data entry only, not medical thresholds (see app/validation.py).
    ts = _as_utc(payload.timestamp) if payload.timestamp else None
    problem = validate_value(meta, payload.value) or validate_timestamp(ts)
    if problem:
        raise HTTPException(422, problem)
    m = Measurement(
        astronaut_id=astronaut_id,
        indicator=payload.indicator,
        value=payload.value,
        timestamp=ts or datetime.now(timezone.utc),
        source="manual",
    )
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


@router.get("/{astronaut_id}/checks")
def get_checks(astronaut_id: int, session: Session = Depends(get_session)):
    """Today's checks: which indicators were measured in the last 24 h."""
    _get_astronaut(astronaut_id, session)
    rows = session.exec(
        select(Measurement.indicator, func.max(Measurement.timestamp))
        .where(Measurement.astronaut_id == astronaut_id)
        .group_by(Measurement.indicator)
    ).all()
    latest = {ind: _as_utc(ts) for ind, ts in rows if ts is not None}
    return compute_checks(latest, indicators())


@router.get("/{astronaut_id}/status")
def get_status(astronaut_id: int, session: Session = Depends(get_session)):
    """Current state of every indicator, with level + reasons."""
    astro = _get_astronaut(astronaut_id, session)
    rows = session.exec(select(Measurement).where(Measurement.astronaut_id == astronaut_id)).all()
    df = pd.DataFrame([r.model_dump() for r in rows])

    # Where the latest value of each indicator comes from (simulated / manual / device).
    latest: dict[str, Measurement] = {}
    for r in rows:
        if r.indicator not in latest or r.timestamp > latest[r.indicator].timestamp:
            latest[r.indicator] = r
    names = _device_names(astronaut_id, session)

    meta = indicators()
    result = []
    for key in meta:
        sub = df[df["indicator"] == key][["timestamp", "value"]] if not df.empty else pd.DataFrame()
        if not sub.empty:
            sub = sub.assign(timestamp=pd.to_datetime(sub["timestamp"], utc=True))
        st = asdict(analyse(key, sub))
        st.update(label=meta[key]["label"], unit=meta[key]["unit"], body_zone=meta[key]["body_zone"])
        last = latest.get(key)
        st["last_source"] = (
            {"type": last.source, "device_name": names.get(last.device_id) if last.device_id else None}
            if last else None
        )
        result.append(st)

    order = {"critical": 0, "attention": 1, "normal": 2, "no_data": 3}
    overall = min((s["level"] for s in result), key=lambda lv: order[lv], default="no_data")
    return {
        "astronaut": astro,
        "overall_level": overall,
        "indicators": result,
        "disclaimer": "Monitoring aid only. This is not a medical diagnosis: "
        "if in doubt, contact your flight surgeon.",
    }
