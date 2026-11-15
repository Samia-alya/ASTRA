"""Generate SIMULATED astronaut data (owner: Member 1).

All values are synthetic and only meant for the demo. They are NOT real
astronaut data and the "typical" values below are NOT medical references.

Usage (from backend/):  python -m scripts.generate_data
    Wipes the database and regenerates fresh data ending 1 hour ago.

The backend also calls seed_if_empty() at startup, so a fresh checkout has demo
data without running this script (disable with HOUSTON_PULSE_NO_SEED=1).
"""
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy.engine import Engine
from sqlmodel import Session, delete, select

from app.config import indicators
from app.database import engine, init_db
from app.models import Astronaut, Measurement

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


def seed(db_engine: Engine) -> None:
    """Replace all astronauts and measurements with freshly generated SIMULATED data."""
    rng = np.random.default_rng(SEED)  # same demo story on every run
    # Last simulated point = 1 hour ago, so new manual entries are always the most recent.
    end = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(hours=1)
    start = end - timedelta(days=DAYS - 1)
    # Round to each indicator's entry step (whole bpm, 0.1 °C, quarter hours…) like a real device,
    # so the simulated data also passes the plausibility validation of manual entries.
    steps = {k: m["input"]["step"] for k, m in indicators().items()}
    with Session(db_engine) as s:
        s.exec(delete(Measurement))
        s.exec(delete(Astronaut))
        for a in ASTRONAUTS:
            astro = Astronaut(name=a["name"], mission=a["mission"], environment=a["environment"], mission_day=87)
            s.add(astro)
            s.flush()
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
                    s.add(Measurement(astronaut_id=astro.id, indicator=ind, value=v,
                                      timestamp=ts, source="simulated"))
        s.commit()


def seed_if_empty(db_engine: Engine) -> bool:
    """Seed only when there is no astronaut yet; never touches existing data. Returns True if seeded."""
    with Session(db_engine) as s:
        if s.exec(select(Astronaut.id).limit(1)).first() is not None:
            return False
    seed(db_engine)
    return True


def main() -> None:
    init_db()
    seed(engine)
    print(f"Generated {DAYS} days of SIMULATED data for {len(ASTRONAUTS)} astronauts.")


if __name__ == "__main__":
    main()
