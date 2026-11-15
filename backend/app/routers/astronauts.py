"""Astronaut, measurement and status endpoints (owner: Member 2)."""
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.analysis.anomaly import analyse, earth_reference_flags
from app.analysis.correlation import evaluate, readiness
from app.analysis.space_baseline import SpaceContext, expected_shift, flight_day, has_model
from app.config import environments, indicators, space_adaptation, thresholds
from app.database import get_session
from app.models import Astronaut, Measurement, MeasurementCreate, PreflightBaseline

router = APIRouter(prefix="/astronauts", tags=["astronauts"])

DISCLAIMER = ("Monitoring aid only. This is not a medical diagnosis: "
              "if in doubt, contact your flight surgeon.")
LEVEL_ORDER = {"critical": 0, "attention": 1, "normal": 2, "no_data": 3}


def _as_utc(dt: datetime) -> datetime:
    """Naive datetimes are assumed to be UTC."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _get_astronaut(astronaut_id: int, session: Session) -> Astronaut:
    astro = session.get(Astronaut, astronaut_id)
    if not astro:
        raise HTTPException(404, f"Astronaut {astronaut_id} not found")
    return astro


def _env(astro: Astronaut) -> dict:
    return environments().get(astro.environment, {})


def _context(astro: Astronaut, preflight: dict[str, float], indicator: str) -> SpaceContext:
    return SpaceContext(
        launch_date=_as_utc(astro.launch_date) if astro.launch_date else None,
        preflight=preflight.get(indicator),
        model_applies=_env(astro).get("adaptation_model_applies", True),
    )


def _preflight(astronaut_id: int, session: Session) -> dict[str, float]:
    rows = session.exec(select(PreflightBaseline).where(PreflightBaseline.astronaut_id == astronaut_id)).all()
    return {r.indicator: r.value for r in rows}


def _frames(astronaut_id: int, session: Session) -> dict[str, pd.DataFrame]:
    """indicator -> DataFrame[timestamp (UTC), value, source], sorted by time."""
    rows = session.exec(select(Measurement).where(Measurement.astronaut_id == astronaut_id)).all()
    df = pd.DataFrame([r.model_dump() for r in rows])
    out: dict[str, pd.DataFrame] = {}
    for key in indicators():
        if df.empty:
            out[key] = pd.DataFrame(columns=["timestamp", "value", "source"])
            continue
        sub = df[df["indicator"] == key][["timestamp", "value", "source"]]
        sub = sub.assign(timestamp=pd.to_datetime(sub["timestamp"], utc=True))
        out[key] = sub.sort_values("timestamp").reset_index(drop=True)
    return out


def _mission(astro: Astronaut) -> dict:
    env = _env(astro)
    fd = flight_day(_as_utc(astro.launch_date), datetime.now(timezone.utc)) if astro.launch_date \
        else astro.mission_day
    return {
        "flight_day": fd,
        "environment": astro.environment,
        "environment_label": env.get("label", astro.environment),
        "comm_delay": env.get("comm_delay"),
        "one_way_delay_min": env.get("one_way_delay_min"),
        "autonomy": env.get("autonomy", "ground_supported"),
        "comm_source": env.get("source"),
        "adaptation_model_applies": env.get("adaptation_model_applies", True),
    }


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


@router.get("/{astronaut_id}/status")
def get_status(astronaut_id: int, session: Session = Depends(get_session)):
    """Current state of every indicator (space-adapted), what an Earth-calibrated
    tool would have said, cross-indicator alerts and readiness."""
    astro = _get_astronaut(astronaut_id, session)
    frames = _frames(astronaut_id, session)
    preflight = _preflight(astronaut_id, session)
    meta = indicators()

    statuses, result = {}, []
    for key in meta:
        sub = frames[key][["timestamp", "value"]]
        ctx = _context(astro, preflight, key)
        space = analyse(key, sub, ctx, mode="space")
        earth = analyse(key, sub, ctx, mode="earth")
        statuses[key] = space
        st = asdict(space)
        st.update(
            label=meta[key]["label"], unit=meta[key]["unit"], body_zone=meta[key]["body_zone"],
            earth_level=earth.level,
            earth_reasons=earth.reasons if earth.level != space.level else [],
            # Alerts an Earth reference value would have raised on normal adaptation.
            earth_false_alarms=earth_reference_flags(key, sub, ctx) if space.space_adjusted else 0,
            adaptation=space_adaptation().get(key) if space.space_adjusted else None,
        )
        result.append(st)

    alerts = evaluate(statuses, frames)
    overall = min((s["level"] for s in result), key=lambda lv: LEVEL_ORDER[lv], default="no_data")
    if alerts and overall == "normal":
        overall = "attention"
    astro.mission_day = _mission(astro)["flight_day"]
    return {
        "astronaut": astro,
        "mission": _mission(astro),
        "overall_level": overall,
        "readiness": readiness(statuses, alerts),
        "alerts": alerts,
        "indicators": result,
        "disclaimer": DISCLAIMER,
    }


@router.get("/{astronaut_id}/trend")
def get_trend(astronaut_id: int, indicator: str, session: Session = Depends(get_session)):
    """History of one indicator by flight day, with the expected in-flight curve."""
    astro = _get_astronaut(astronaut_id, session)
    if indicator not in indicators():
        raise HTTPException(422, f"Unknown indicator '{indicator}'")
    df = _frames(astronaut_id, session)[indicator]
    ctx = _context(astro, _preflight(astronaut_id, session), indicator)
    modelled = has_model(indicator) and ctx.model_applies and ctx.launch_date is not None
    status = analyse(indicator, df[["timestamp", "value"]], ctx, mode="space")
    half_band = None
    if status.band_high is not None and status.baseline is not None:
        half_band = round(status.band_high - status.baseline, 3)
    # Personal offset: this astronaut's own level relative to the model curve.
    offset = 0.0
    if modelled and ctx.preflight is not None and status.baseline is not None and status.expected is not None:
        offset = status.baseline - status.expected

    points = []
    for row in df.itertuples():
        fd = flight_day(ctx.launch_date, row.timestamp) if ctx.launch_date else None
        expected = None
        if modelled and ctx.preflight is not None and fd is not None:
            expected = round(ctx.preflight + expected_shift(indicator, fd) + offset, 2)
        elif status.baseline is not None:
            expected = status.baseline
        points.append({
            "timestamp": row.timestamp.isoformat(), "flight_day": fd, "value": row.value,
            "source": row.source, "expected": expected,
        })
    t = thresholds().get(indicator, {})
    return {
        "indicator": indicator,
        "points": points,
        "preflight": ctx.preflight,
        "half_band": half_band,
        "space_adjusted": modelled,
        "adaptation": space_adaptation().get(indicator) if modelled else None,
        "earth_reference_high": t.get("reference_high"),
        "earth_reference_low": t.get("reference_low"),
        "critical_high": t.get("critical_high"),
        "critical_low": t.get("critical_low"),
    }


@router.get("/{astronaut_id}/report")
def get_report(astronaut_id: int, session: Session = Depends(get_session)):
    """Self-contained summary to send to Mission Control when a live
    conversation is not possible (store-and-forward)."""
    status = get_status(astronaut_id, session)
    return {
        "schema": "astrovitals-report/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "data_notice": "Prototype. Values are SIMULATED unless entered manually.",
        **status,
    }
