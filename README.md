# Houston Pulse

Health monitoring software for astronauts on long-duration missions — NASA Space Apps Challenge 2026.

> ⚠️ All data in this prototype is **SIMULATED**. Houston Pulse is a monitoring aid, not a medical diagnosis tool.

## Structure

```
backend/                 FastAPI + SQLite (Python)
  app/main.py            app entry point, CORS, routers
  app/models.py          tables: Astronaut, Measurement           (Member 2)
  app/routers/           REST endpoints                           (Member 2)
  app/analysis/anomaly.py  baseline + trend + thresholds           (Member 1)
  app/config/indicators.json   indicator metadata + explanations
  app/config/thresholds.json   documented medical thresholds (sources required!)
  scripts/generate_data.py     simulated demo data                (Member 1)
frontend/                Vue 3 + TypeScript + Vite + Plotly       (Member 3)
  src/api.ts             all API calls
  src/types.ts           types shared with the backend contract
  src/components/        IndicatorCard, HistoryChart, MeasurementForm
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
| GET | `/astronauts/{id}/status` | per-indicator `value`, `baseline`, `level`, `trend`, `reasons[]` + `overall_level` |
| GET | `/astronauts/{id}/measurements?indicator=&start=&end=` | history |
| POST | `/astronauts/{id}/measurements` | body `{indicator, value, timestamp?}` → stored with `source: "manual"` |
| GET | `/indicators` | metadata, explanations, sources |

Any change to this contract must be updated in **both** `backend/app/routers/` and `frontend/src/types.ts`.

## Analysis rules

1. **Personal baseline** — reference period = the 10 days before the last 5 days. Today's value ≥ 2.5 standard deviations away (in the direction that matters, see `watch_direction`) → `attention`.
2. **Trend** — significant linear trend (p < 0.05) over the last 5 days → `attention`.
3. **Documented thresholds** (`thresholds.json`) — the **only** rule that can trigger `critical`. Fill a value only with a verified source (organisation + URL).

Rules 1–2 are statistical choices, not medical thresholds.
