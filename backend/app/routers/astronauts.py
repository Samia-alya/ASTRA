"""Astronaut, measurement and status endpoints (owner: Member 2)."""
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from app.analysis.anomaly import analyse
from app.analysis.checks import compute_checks
from app.config import indicators
from app.database import get_session
from app.models import Astronaut, Measurement, MeasurementCreate

router = APIRouter(prefix="/astronauts", tags=["astronauts"])


def _as_utc(dt: datetime) -> datetime:
    """Naive datetimes are assumed to be UTC."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _get_astronaut(astronaut_id: int, session: Session) -> Astronaut:
    astro = session.get(Astronaut, astronaut_id)
    if not astro:
        raise HTTPException(404, f"Astronaut {astronaut_id} not found")
    return astro


@router.get("", response_model=list[Astronaut])
def list_astronauts(session: Session = Depends(get_session)):
    return session.exec(select(Astronaut)).all()


@router.get("/{astronaut_id}/measurements", response_model=list[Measurement])
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
    return session.exec(q.order_by(Measurement.timestamp)).all()


@router.post("/{astronaut_id}/measurements", response_model=Measurement, status_code=201)
def add_measurement(
    astronaut_id: int, payload: MeasurementCreate, session: Session = Depends(get_session)
):
    _get_astronaut(astronaut_id, session)
    if payload.indicator not in indicators():
        raise HTTPException(422, f"Unknown indicator '{payload.indicator}'")
    m = Measurement(
        astronaut_id=astronaut_id,
        indicator=payload.indicator,
        value=payload.value,
        timestamp=_as_utc(payload.timestamp) if payload.timestamp else datetime.now(timezone.utc),
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

    meta = indicators()
    result = []
    for key in meta:
        sub = df[df["indicator"] == key][["timestamp", "value"]] if not df.empty else pd.DataFrame()
        if not sub.empty:
            sub = sub.assign(timestamp=pd.to_datetime(sub["timestamp"], utc=True))
        st = asdict(analyse(key, sub))
        st.update(label=meta[key]["label"], unit=meta[key]["unit"], body_zone=meta[key]["body_zone"])
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
