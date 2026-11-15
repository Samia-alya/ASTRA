# AstroVitals

Health monitoring software for astronauts on long-duration missions — NASA Space Apps Challenge 2026.

> ⚠️ All data in this prototype is **SIMULATED**. AstroVitals is a monitoring aid, not a medical diagnosis tool.

## What makes it different

1. **Space-adapted baseline.** A healthy body in weightlessness settles on values an Earth-calibrated tool reads as illness (resting core temperature about 1 °C higher, blood pressure 8-10 mmHg lower). AstroVitals removes the *expected* in-flight change before judging a value, shows what an Earth tool would have said, and counts the false alarms avoided.
2. **Masked fatigue.** A playable 3-minute reaction test (PVT-B) is compared with how alert the astronaut says they feel and with recent sleep. Feeling fine while performing worse blocks critical operations.
3. **Explained cross-indicator alerts** with evidence, suggested next steps and sources, plus a GO / CAUTION / NO-GO readiness status and an exportable report for when Earth is too far to answer in time.

## Structure

```
backend/                 FastAPI + SQLite (Python)
  app/main.py            app entry point, CORS, routers
  app/models.py          tables: Astronaut, PreflightBaseline, Measurement   (Member 2)
  app/routers/           REST endpoints                                      (Member 2)
  app/analysis/anomaly.py         baseline + trend + thresholds              (Member 1)
  app/analysis/space_baseline.py  expected in-flight change per flight day
  app/analysis/correlation.py     cross-indicator rules + readiness
  app/config/indicators.json         indicator metadata + explanations
  app/config/thresholds.json         reference and critical thresholds (sources required!)
  app/config/space_adaptation.json   sourced in-flight adaptation model
  app/config/correlation_rules.json  rule parameters, wording, actions, sources
  app/config/environments.json       mission environments, communication delay
  scripts/generate_data.py     simulated demo data                (Member 1)
  tests/                       python -m pytest -q
frontend/                Vue 3 + TypeScript + Vite + Plotly + Three.js   (Member 3)
  src/api.ts             all API calls
  src/types.ts           types shared with the backend contract
  src/components/        HolographicBody3D (Three.js), MetricPanel, HistoryChart, AlertsPanel,
                         ModalDialog, PvtTest, MeasurementForm; body/humanoid.ts builds the 3D figure
docs/SOURCES.md          every number used, with its source and what is an assumption
docs/SUBMISSION_DRAFT.md draft text for the Space Apps project page
```

## Run it

Two terminals.

**Backend** (Python 3.10+):
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.generate_data      # (re)creates simulated data
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

**Frontend** (Node 20+):
```bash
cd frontend
npm install
npm run dev
```
App: http://localhost:5173 (calls to `/api/*` are proxied to the backend).

## API contract

| Method | Route | Description |
|---|---|---|
| GET | `/astronauts` | list profiles |
| GET | `/astronauts/{id}/status` | `mission`, `readiness`, `alerts[]`, `overall_level`, and per indicator: `value`, `baseline`, `level`, `trend`, `reasons[]`, `preflight`, `expected`, `earth_level`, `earth_false_alarms` |
| GET | `/astronauts/{id}/trend?indicator=` | history by flight day with the expected in-flight curve and band |
| GET | `/astronauts/{id}/report` | self-contained JSON summary for Mission Control |
| GET | `/astronauts/{id}/measurements?indicator=&start=&end=` | history |
| POST | `/astronauts/{id}/measurements` | body `{indicator, value, timestamp?}` → stored with `source: "manual"` |
| GET | `/indicators` | metadata, explanations, sources |

Any change to this contract must be updated in **both** `backend/app/routers/` and `frontend/src/types.ts`.
The database schema changed (launch date, pre-flight baselines): rerun `python -m scripts.generate_data`.

## Analysis rules

1. **Personal baseline** — reference period = the 10 days before the last 5 days. Today's value ≥ 2.5 standard deviations away (in the direction that matters, see `watch_direction`) → `attention`.
2. **Trend** — significant linear trend (p < 0.05) over the last 5 days whose total change is at least 2 baseline standard deviations → `attention`.
3. **Reference values** (`thresholds.json`, `reference_*`) — Earth clinical references → `attention`.
4. **Critical limits** (`thresholds.json`, `critical_*`) — the **only** rule that can trigger `critical`. Fill a value only with a verified source (organisation + URL).
5. **Space adaptation** (`space_adaptation.json`) — for temperature and blood pressure, the expected in-flight change is removed before rules 1-3. Critical limits are never adjusted.
6. **Cross-indicator rules** (`correlation_rules.json`) — combine weak signals into one explained alert. Never `critical`.

Rules 1-2 are statistical choices, not medical thresholds. The combinations in rule 6 are team hypotheses built on cited findings and are not clinically validated. See `docs/SOURCES.md`.

## Known limits

- All data is simulated. No real astronaut data is used.
- On pure noise, rules 1-2 still flag roughly 7% of indicator-days. With ten indicators that is frequent; the thresholds need tuning on real data.
- The adaptation model comes from ISS (weightlessness) measurements and is not applied to partial gravity.
- The browser reaction test is not hardware-calibrated.
