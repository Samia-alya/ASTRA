"""Generate SIMULATED astronaut data (owner: Member 1).

All values are synthetic and only meant for the demo. They are NOT real
astronaut data. Where a simulated in-flight drift follows a published finding
(core temperature, blood pressure), it uses the same sourced model as the
analysis (config/space_adaptation.json); everything else (noise levels,
personal baselines, the demo scenarios) is invented for the demo.

Usage (from backend/):  python -m scripts.generate_data
"""
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlmodel import Session, SQLModel

from app.analysis.space_baseline import expected_shift
from app.database import engine, init_db
from app.models import Astronaut, Measurement, PreflightBaseline

# Seed chosen so the three demo stories are clean on the last day (no chance flags).
rng = np.random.default_rng(3)

# Day-to-day noise per indicator (synthetic, for the demo only).
NOISE = {
    "heart_rate": 2.0, "bp_systolic": 3.0, "bp_diastolic": 2.5, "glucose": 3.5,
    "temperature": 0.08, "sleep_hours": 0.30, "mood": 0.35, "alertness": 0.5,
    "pvt_lapses": 0.7, "pvt_mean_rt": 6.0,
}
INTEGER = {"mood": (1, 5), "alertness": (0, 10), "pvt_lapses": (0, 50)}

# Each astronaut: pre-flight values on Earth (invented), how many days in flight,
# and a demo scenario = {indicator: [values for the LAST len(list) days]} added on top.
ASTRONAUTS = [
    {
        # Demo case: fatigue the astronaut does not feel + temperature above the
        # space-adapted baseline. In flight for 145 days on the way to Mars.
        "name": "Cmdr. A. Rivera", "mission": "Mars Transit (simulated)",
        "environment": "mars_transit", "flight_days": 145,
        "preflight": {"heart_rate": 62, "bp_systolic": 118, "bp_diastolic": 76, "glucose": 88,
                      "temperature": 37.0, "sleep_hours": 6.8, "mood": 4, "alertness": 7,
                      "pvt_lapses": 1, "pvt_mean_rt": 224},
        "final_days": {
            "sleep_hours": [6.1, 5.8, 5.6, 5.4, 5.3, 5.1],
            "pvt_lapses": [1, 2, 2, 3, 4, 5],
            "pvt_mean_rt": [231, 238, 246, 253, 261, 268],
            "alertness": [7, 7, 7, 7, 7, 7],
            "temperature": [38.1, 38.2, 38.3, 38.4, 38.5],
            "heart_rate": [65, 67, 69, 71, 72, 74],
            "mood": [4, 4, 3, 3, 3, 3],
        },
    },
    {
        # Healthy and fully adapted: resting temperature around 38 °C is NORMAL at
        # flight day 100. An Earth-calibrated tool would call it a fever every day.
        "name": "Dr. K. Tanaka", "mission": "ISS Expedition (simulated)",
        "environment": "station", "flight_days": 100,
        "preflight": {"heart_rate": 58, "bp_systolic": 116, "bp_diastolic": 74, "glucose": 90,
                      "temperature": 37.1, "sleep_hours": 7.0, "mood": 4, "alertness": 8,
                      "pvt_lapses": 1, "pvt_mean_rt": 218},
        "final_days": {},
    },
    {
        # Early in the mission: still adapting, with a rising systolic pressure.
        "name": "Eng. L. Moreau", "mission": "ISS Expedition (simulated)",
        "environment": "station", "flight_days": 40,
        "preflight": {"heart_rate": 64, "bp_systolic": 120, "bp_diastolic": 78, "glucose": 92,
                      "temperature": 36.9, "sleep_hours": 6.9, "mood": 4, "alertness": 7,
                      "pvt_lapses": 1, "pvt_mean_rt": 230},
        "final_days": {"bp_systolic": [121, 124, 127, 130, 133]},
    },
]


def main() -> None:
    SQLModel.metadata.drop_all(engine)  # schema may have changed since the last run
    init_db()
    # Last simulated point one hour ago, so a measurement entered now is the newest.
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    with Session(engine) as s:
        for a in ASTRONAUTS:
            n = a["flight_days"]
            launch = end - timedelta(days=n - 1)
            astro = Astronaut(name=a["name"], mission=a["mission"], environment=a["environment"],
                              mission_day=n, launch_date=launch)
            s.add(astro)
            s.flush()
            for ind, pre in a["preflight"].items():
                s.add(PreflightBaseline(astronaut_id=astro.id, indicator=ind, value=pre))
                scenario = a["final_days"].get(ind, [])
                for fd in range(1, n + 1):
                    ts = launch + timedelta(days=fd - 1)
                    k = fd - (n - len(scenario)) - 1  # index into the scenario, if in it
                    if 0 <= k < len(scenario):
                        v = float(scenario[k])
                    else:
                        v = pre + expected_shift(ind, fd) + rng.normal(0, NOISE[ind])
                        if ind in INTEGER:
                            lo, hi = INTEGER[ind]
                            v = float(np.clip(round(v), lo, hi))
                    s.add(Measurement(astronaut_id=astro.id, indicator=ind, value=round(float(v), 2),
                                      timestamp=ts, source="simulated"))
        s.commit()
    print(f"Generated SIMULATED data for {len(ASTRONAUTS)} astronauts "
          f"({', '.join(str(a['flight_days']) for a in ASTRONAUTS)} flight days).")


if __name__ == "__main__":
    main()
