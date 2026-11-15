"""Generate SIMULATED astronaut data (owner: Member 1).

All values are synthetic and only meant for the demo. They are NOT real
astronaut data and the "typical" values below are NOT medical references.

Usage (from backend/):  python -m scripts.generate_data
    Wipes the database and regenerates fresh data ending 1 hour ago.

The backend also calls seed_if_empty() at startup, so a fresh checkout has demo
data without running this script (disable with HOUSTON_PULSE_NO_SEED=1).
"""
import secrets
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, delete, select

from app.config import indicators
from app.database import engine, init_db
from app.models import Astronaut, Device, Measurement

DAYS = 30
SEED = 42

# Simulation centre values and noise (synthetic, for the demo only).
SIM = {
    "heart_rate": (64, 3),
    "bp_systolic": (118, 4),
    "bp_diastolic": (76, 3),
    "glucose": (92, 5),
    "temperature": (36.7, 0.15),
    "sleep_hours": (7.0, 0.4),
    "mood": (4.0, 0.4),
}

# Demo scenarios: (indicator, drift per day applied over the last N days)
ASTRONAUTS = [
    {"name": "Cmdr. A. Rivera", "mission": "Artemis Base Camp (simulated)", "environment": "lunar_base",
     "scenario": {"sleep_hours": (-0.3, 7), "mood": (-0.25, 7), "heart_rate": (1.5, 6)},
     # Today's checks demo: these were not measured on the last simulated day.
     "skip_last_day": {"glucose", "temperature"}},
    {"name": "Dr. K. Tanaka", "mission": "ISS Expedition (simulated)", "environment": "station",
     "scenario": {}},
    {"name": "Eng. L. Moreau", "mission": "Mars Transit (simulated)", "environment": "mars_transit",
     # Mars transit: rising temperature (crosses the documented fever threshold) + rising BP
     "scenario": {"temperature": (0.5, 3), "bp_systolic": (2.0, 5)}},
]

# Every crew member carries the same standard kit of SIMULATED devices (kind, name).
KIT = [
    ("smart_shirt", "Bio-Monitor shirt (simulated)"),
    ("actigraphy_band", "Sleep band (simulated)"),
    ("bp_cuff", "BP cuff (simulated)"),
    ("thermometer", "Thermometer (simulated)"),
    ("glucometer", "Glucometer (simulated)"),
]
# Which device the generated history of each indicator comes from. The cuff is the reference for
# blood pressure (the shirt's systolic is not duplicated). Mood is self-reported: no device, so it
# stays a plain "simulated" row.
GENERATED_BY = {
    "heart_rate": "smart_shirt",
    "sleep_hours": "actigraphy_band",
    "bp_systolic": "bp_cuff",
    "bp_diastolic": "bp_cuff",
    "temperature": "thermometer",
    "glucose": "glucometer",
}


def seed(db_engine: Engine) -> list[tuple[int, str, str, str]]:
    """Replace all astronauts, devices and measurements with freshly generated SIMULATED data.

    Never drops tables (it also runs at API startup via seed_if_empty). Returns the created
    devices as (id, astronaut name, device name, token).
    """
    rng = np.random.default_rng(SEED)  # same demo story on every run
    # Last simulated point = 1 hour ago, so new manual entries are always the most recent.
    end = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(hours=1)
    start = end - timedelta(days=DAYS - 1)
    # Round to each indicator's entry step (whole bpm, 0.1 °C, quarter hours…) like a real device,
    # so the simulated data also passes the plausibility validation of manual entries.
    steps = {k: m["input"]["step"] for k, m in indicators().items()}
    with Session(db_engine) as s:
        s.exec(delete(Measurement))
        s.exec(delete(Device))
        s.exec(delete(Astronaut))
        created: list[tuple[str, Device]] = []
        for a in ASTRONAUTS:
            astro = Astronaut(name=a["name"], mission=a["mission"], environment=a["environment"], mission_day=87)
            s.add(astro)
            s.flush()
            # Devices use `secrets`, not `rng`, so the simulated values stay identical.
            kit: dict[str, Device] = {}
            for kind, name in KIT:
                dev = Device(astronaut_id=astro.id, kind=kind, name=name, token=secrets.token_urlsafe(24))
                s.add(dev)
                kit[kind] = dev
                created.append((a["name"], dev))
            s.flush()  # device ids
            source_of = {ind: kit[kind] for ind, kind in GENERATED_BY.items()}
            last_reading: dict[int, datetime] = {}
            for d in range(DAYS):
                ts = start + timedelta(days=d)
                for ind, (centre, noise) in SIM.items():
                    v = centre + rng.normal(0, noise)
                    if ind in a["scenario"]:
                        slope, n = a["scenario"][ind]
                        days_in = d - (DAYS - n)
                        if days_in >= 0:
                            v += slope * (days_in + 1)
                    if ind == "mood":
                        v = float(np.clip(round(v), 1, 5))
                    # Skip after drawing the value, so every other value stays identical.
                    if d == DAYS - 1 and ind in a.get("skip_last_day", ()):
                        continue
                    v = round(round(float(v) / steps[ind]) * steps[ind], 2)
                    dev = source_of.get(ind)
                    s.add(Measurement(astronaut_id=astro.id, indicator=ind, value=v, timestamp=ts,
                                      source="device" if dev else "simulated",
                                      device_id=dev.id if dev else None))
                    if dev:
                        last_reading[dev.id] = max(ts, last_reading.get(dev.id, ts))
            # A device was last seen when it sent its latest generated reading (Rivera's glucometer
            # and thermometer: the day before, since her glucose and temperature checks are due).
            for dev in kit.values():
                dev.last_seen = last_reading.get(dev.id)
        s.commit()
        # Read the values while the session is still open (the objects expire after it closes).
        return [(dev.id, astro_name, dev.name, dev.token) for astro_name, dev in created]


def seed_if_empty(db_engine: Engine) -> bool:
    """Seed only when there is no astronaut yet; never touches existing data. Returns True if seeded."""
    with Session(db_engine) as s:
        if s.exec(select(Astronaut.id).limit(1)).first() is not None:
            return False
    seed(db_engine)
    return True


def main() -> None:
    # Run by hand, the generator rebuilds everything, so it also recreates the tables: an old database
    # file with an outdated schema (e.g. before devices existed) is upgraded by simply re-running it.
    SQLModel.metadata.drop_all(engine)
    init_db()
    devices = seed(engine)
    print(f"Generated {DAYS} days of SIMULATED data for {len(ASTRONAUTS)} astronauts.")
    print()
    print("SIMULATED devices (id, astronaut, name, token for X-Device-Token):")
    for dev_id, astro_name, dev_name, token in devices:
        print(f"  {dev_id:>2}  {astro_name:<16} {dev_name:<30} {token}")


if __name__ == "__main__":
    main()
