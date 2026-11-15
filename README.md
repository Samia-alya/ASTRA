# Houston Pulse

Health monitoring software for astronauts on long-duration missions — NASA Space Apps Challenge 2026,
challenge *Create Health Monitoring Software for Astronauts on Space Missions*.

Far from Earth, astronauts must spot changes in their own health. Houston Pulse collects six health
indicators, compares each one with the astronaut's **own baseline**, flags unusual changes, explains
**why** in plain language, and says **what to do next** — including when to contact the flight surgeon.

> ⚠️ All astronaut data in this prototype is **SIMULATED**. Houston Pulse is a monitoring aid, not a medical diagnosis tool.

## Features

- **Vital ring** — one arc per indicator around a body silhouette, colour-coded (Nominal / Watch / Critical). The heart beats at the latest measured heart rate; flagged body zones pulse.
- **Personal baselines** — each astronaut is compared with their own recent history, not a population average.
- **Explained alerts** — every flag comes with a sentence saying why.
- **Guidance** — what the indicator measures, why it matters in space (NASA Human Research Program), and what to do now.
- **Mission context** — environment (orbit, lunar base, Mars transit) and one-way signal delay to Earth.
- **Manual entry** — log a new measurement; the analysis updates instantly.

## Indicators and analysis

The six indicators are the ones suggested by the challenge: heart rate, blood pressure (systolic and diastolic), blood glucose, body temperature, sleep and mood.

| Level | Rule |
|---|---|
| **Watch** (`attention`) | Today's value is ≥ 2.5 standard deviations from the personal baseline (10 days before the last 5), **or** a significant trend (p < 0.05) over the last 5 days — only in the direction that matters (e.g. less sleep, not more). These are statistical rules, not medical thresholds. |
| **Critical** | The value crosses a **documented reference threshold** (`backend/app/config/thresholds.json`). This is the only rule that can trigger Critical. |

### Reference thresholds (general adult population — not spaceflight flight rules, which are not public)

| Indicator | Critical if | Source |
|---|---|---|
| Heart rate | > 100 bpm at rest (tachycardia) | [American Heart Association](https://www.heart.org/en/health-topics/high-blood-pressure/the-facts-about-high-blood-pressure/all-about-heart-rate-pulse) |
| Blood pressure | > 180 systolic and/or > 120 diastolic (hypertensive crisis) | [American Heart Association](https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings) |
| Blood pressure | < 90 systolic or < 60 diastolic (low blood pressure) | [NHLBI](https://www.nhlbi.nih.gov/health/low-blood-pressure) |
| Blood glucose | < 54 mg/dL (level 2 hypoglycemia) | [ADA / EASD, Diabetes Care 2017](https://doi.org/10.2337/dc16-2215) |
| Blood glucose | > 240 mg/dL (check for ketones) | [American Diabetes Association](https://diabetes.org/living-with-diabetes/treatment-care/hyperglycemia) |
| Body temperature | ≥ 38.0 °C (fever) | [CDC](https://www.cdc.gov/port-health/php/definitions-symptoms-reportable-illness/index.html) |
| Body temperature | < 35.0 °C (hypothermia, emergency) | [CDC](https://www.cdc.gov/winter-weather/prevention/index.html) |
| Sleep | none — ≥ 7 h recommended, used in guidance only | [CDC / AASM](https://archive.cdc.gov/www_cdc_gov/media/releases/2016/p0215-enough-sleep.html) |
| Mood | none — self-reported 1–5 scale, not a clinical instrument | — |

Space context for each indicator comes from the [NASA Human Research Program risks](https://www.nasa.gov/hrp/risks/).

## Demo data

`backend/scripts/generate_data.py` creates 30 days of **simulated** data for three crew members:

| Crew member | Environment | Story | Overall |
|---|---|---|---|
| Dr. K. Tanaka | Low Earth orbit | Everything steady | Nominal |
| Cmdr. A. Rivera | Lunar base | Sleep and mood dropping, resting heart rate rising | Watch |
| Eng. L. Moreau | Mars transit (3–22 min delay) | Temperature rising past 38 °C, blood pressure trending up | Critical |

## Structure

```
backend/                       FastAPI + SQLite (Python)
  app/main.py                  app entry point, CORS, routers
  app/models.py                tables: Astronaut, Measurement
  app/routers/                 REST endpoints
  app/analysis/anomaly.py      baseline + trend + documented thresholds
  app/config/indicators.json   labels, explanations, guidance, sources
  app/config/thresholds.json   documented reference thresholds (with sources)
  scripts/generate_data.py     simulated demo data
  tests/                       pytest suite (analysis rules + API)
frontend/                      Vue 3 + TypeScript + Vite + Plotly
  src/App.vue                  page layout and headline logic
  src/components/VitalRing.vue ring + body silhouette
  src/components/IndicatorGrid.vue, HistoryChart.vue, MeasurementForm.vue
  src/api.ts, src/types.ts     API client and shared types
```

## Run it

**Backend** (Python 3.10+):
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.generate_data      # (re)creates the simulated data
uvicorn app.main:app --reload --port 8000
python -m pytest -q                  # run the tests
```
API docs: http://localhost:8000/docs

**Frontend** (Node 20+):
```bash
cd frontend
npm install
npm run dev
```
App: http://localhost:5173

## API

| Method | Route | Description |
|---|---|---|
| GET | `/astronauts` | list crew members |
| GET | `/astronauts/{id}/status` | per indicator: `value`, `baseline`, `level`, `trend`, `reasons[]`, plus `overall_level` |
| GET | `/astronauts/{id}/measurements?indicator=&start=&end=` | history |
| POST | `/astronauts/{id}/measurements` | body `{indicator, value, timestamp?}`, stored with `source: "manual"` |
| GET | `/indicators` | metadata, explanations, guidance, sources |

## Next steps

Other risks identified by NASA's Human Research Program that Houston Pulse could monitor next:
radiation dose (personal dosimeter), blood oxygen saturation (hypoxia risk), daily exercise
(bone and muscle loss countermeasure), and vision checks (Spaceflight Associated Neuro-ocular Syndrome).
