"""Optional in-process live mode for the demo (HP_SIMULATE_DEVICES=1). SIMULATED data only.

Every 5 s, each smart_shirt device sends one heart rate reading: small random noise around the
heart rate it had when the backend started. Readings go through the same validation and storage
as POST /devices/{id}/readings (see ingest_readings). Off by default and always off in tests.
"""
from __future__ import annotations

import asyncio
import logging
import random

from fastapi import HTTPException
from sqlmodel import Session, select

from app import database
from app.models import Device, Measurement, ReadingIn
from app.routers.devices import ingest_readings

INTERVAL_S = 5.0
NOISE_BPM = 1.5
DEFAULT_BPM = 65.0
log = logging.getLogger("houston_pulse.live_devices")


def _base_heart_rate(session: Session, device: Device) -> float:
    """Latest heart rate sent by this device, else the astronaut's latest, else a default."""
    for cond in (Measurement.device_id == device.id, Measurement.astronaut_id == device.astronaut_id):
        m = session.exec(
            select(Measurement).where(cond, Measurement.indicator == "heart_rate")
            .order_by(Measurement.timestamp.desc()).limit(1)
        ).first()
        if m:
            return m.value
    return DEFAULT_BPM


def tick(bases: dict[int, float]) -> None:
    """Send one reading per smart shirt. `bases` keeps each shirt's starting value (no random walk)."""
    with Session(database.engine) as s:
        for dev in s.exec(select(Device).where(Device.kind == "smart_shirt")).all():
            base = bases.setdefault(dev.id, _base_heart_rate(s, dev))
            value = float(max(20, min(250, round(base + random.gauss(0, NOISE_BPM)))))
            try:
                ingest_readings(s, dev, [ReadingIn(indicator="heart_rate", value=value)])
            except HTTPException as e:
                log.warning("live device %s: reading rejected: %s", dev.id, e.detail)


async def run_live_devices(interval: float = INTERVAL_S) -> None:
    bases: dict[int, float] = {}
    log.warning("HP_SIMULATE_DEVICES=1: SIMULATED smart shirts send a heart rate every %.0f s", interval)
    while True:
        try:
            await asyncio.to_thread(tick, bases)  # SQLite work off the event loop
        except Exception:  # keep the demo running whatever happens
            log.exception("live device tick failed")
        await asyncio.sleep(interval)
