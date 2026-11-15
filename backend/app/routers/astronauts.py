"""Astronaut, measurement and status endpoints (owner: Member 2)."""
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from app.analysis.anomaly import analyse
from app.analysis.autonomy import autonomy_state, episode_start
from app.analysis.checks import compute_checks
from app.config import autonomy_rule, indicators
from app.database import get_session
from app.models import Astronaut, AutonomyAction, Measurement, MeasurementCreate, ReportTransmission
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


def _statuses(astronaut_id: int, session: Session) -> tuple[list[dict], str]:
    """Per-indicator status (level + reasons) and the overall level."""
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
    return result, overall


@router.get("/{astronaut_id}/checks")
def get_checks(astronaut_id: int, session: Session = Depends(get_session)):
    """Today's checks: which indicators were measured in the last 24 h
    (every 2 h for critical indicators in Earth-independent mode)."""
    astro = _get_astronaut(astronaut_id, session)
    rows = session.exec(
        select(Measurement.indicator, func.max(Measurement.timestamp))
        .where(Measurement.astronaut_id == astronaut_id)
        .group_by(Measurement.indicator)
    ).all()
    latest = {ind: _as_utc(ts) for ind, ts in rows if ts is not None}
    statuses, overall = _statuses(astronaut_id, session)
    tight: set[str] = set()
    if autonomy_state(overall, astro.environment)["active"]:
        tight = {s["indicator"] for s in statuses if s["level"] == "critical"}
    return compute_checks(latest, indicators(), tight=tight,
                          tight_hours=autonomy_rule()["tight_check_interval_hours"])


@router.get("/{astronaut_id}/status")
def get_status(astronaut_id: int, session: Session = Depends(get_session)):
    """Current state of every indicator, with level + reasons, and the Earth-independent mode block."""
    astro = _get_astronaut(astronaut_id, session)
    result, overall = _statuses(astronaut_id, session)
    return {
        "astronaut": astro,
        "overall_level": overall,
        "indicators": result,
        "autonomy": autonomy_state(overall, astro.environment),
        "disclaimer": "Monitoring aid only. This is not a medical diagnosis: "
        "if in doubt, contact your flight surgeon.",
    }


# --- Earth-independent mode ---------------------------------------------------
# Only actions and reports of the current episode (last 24 h, see analysis/autonomy.py) count.


def _episode_actions(astronaut_id: int, session: Session) -> list[AutonomyAction]:
    return session.exec(
        select(AutonomyAction)
        .where(AutonomyAction.astronaut_id == astronaut_id, AutonomyAction.timestamp >= episode_start())
        .order_by(AutonomyAction.timestamp)
    ).all()


def _last_report(astronaut_id: int, session: Session) -> Optional[datetime]:
    sent = session.exec(
        select(func.max(ReportTransmission.sent_at)).where(
            ReportTransmission.astronaut_id == astronaut_id, ReportTransmission.sent_at >= episode_start()
        )
    ).first()
    return _as_utc(sent) if sent else None


@router.get("/{astronaut_id}/autonomy")
def get_autonomy(astronaut_id: int, session: Session = Depends(get_session)):
    """Onboard steps for each critical indicator, with when each step was checked, and the last report sent."""
    astro = _get_astronaut(astronaut_id, session)
    statuses, overall = _statuses(astronaut_id, session)
    checked = {(a.indicator, a.step_index): _as_utc(a.timestamp) for a in _episode_actions(astronaut_id, session)}
    meta = indicators()
    groups = []
    for s in statuses:
        steps = meta[s["indicator"]].get("autonomy_steps")
        if s["level"] != "critical" or not steps:
            continue
        groups.append({
            "indicator": s["indicator"],
            "label": s["label"],
            "steps": [
                {"index": i, "text": text,
                 "checked_at": checked[(s["indicator"], i)].isoformat() if (s["indicator"], i) in checked else None}
                for i, text in enumerate(steps)
            ],
        })
    sent = _last_report(astronaut_id, session)
    return {
        "autonomy": autonomy_state(overall, astro.environment),
        "groups": groups,
        "report_sent_at": sent.isoformat() if sent else None,
    }


def _check_step(indicator: str, step_index: int) -> None:
    steps = indicators().get(indicator, {}).get("autonomy_steps")
    if not steps:
        raise HTTPException(404, f"No onboard steps for indicator '{indicator}'")
    if not 0 <= step_index < len(steps):
        raise HTTPException(404, f"Step {step_index} does not exist for '{indicator}'")


@router.put("/{astronaut_id}/autonomy/actions/{indicator}/{step_index}")
def check_step(astronaut_id: int, indicator: str, step_index: int, session: Session = Depends(get_session)):
    """Check an onboard step (idempotent: an already checked step keeps its original time)."""
    _get_astronaut(astronaut_id, session)
    _check_step(indicator, step_index)
    existing = next((a for a in _episode_actions(astronaut_id, session)
                     if a.indicator == indicator and a.step_index == step_index), None)
    if existing is None:
        existing = AutonomyAction(astronaut_id=astronaut_id, indicator=indicator, step_index=step_index,
                                  timestamp=datetime.now(timezone.utc))
        session.add(existing)
        session.commit()
        session.refresh(existing)
    return {"indicator": indicator, "step_index": step_index, "checked_at": _as_utc(existing.timestamp).isoformat()}


@router.delete("/{astronaut_id}/autonomy/actions/{indicator}/{step_index}", status_code=204)
def uncheck_step(astronaut_id: int, indicator: str, step_index: int, session: Session = Depends(get_session)):
    """Uncheck an onboard step."""
    _get_astronaut(astronaut_id, session)
    _check_step(indicator, step_index)
    for a in _episode_actions(astronaut_id, session):
        if a.indicator == indicator and a.step_index == step_index:
            session.delete(a)
    session.commit()


@router.post("/{astronaut_id}/autonomy/report", status_code=201)
def send_report(astronaut_id: int, session: Session = Depends(get_session)):
    """Record that a crew health report was sent to Earth now."""
    _get_astronaut(astronaut_id, session)
    t = ReportTransmission(astronaut_id=astronaut_id, sent_at=datetime.now(timezone.utc))
    session.add(t)
    session.commit()
    return {"report_sent_at": _as_utc(t.sent_at).isoformat()}
