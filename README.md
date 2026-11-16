# Houston Pulse

Health monitoring software for astronauts on long-duration missions — NASA Space Apps Challenge 2026,
challenge *Create Health Monitoring Software for Astronauts on Space Missions*.

**Team SpaceMed3** — Samia Al Yahiaoui, Nourhane Anani, Teddy Emmanuel Kana Boumkwo II.

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
- **Earth-independent mode** — on a critical alert far from Earth, the app guides the crew through onboard monitoring steps while a report travels to Earth ([details](#earth-independent-mode)).
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

`backend/scripts/generate_data.py` creates 30 days of **simulated** data for three crew members.
The backend generates it automatically on startup when the database is empty; existing data
(including manual entries) is never overwritten.

| Crew member | Environment | Story | Overall |
|---|---|---|---|
| Dr. K. Tanaka | Low Earth orbit | Everything steady | Nominal |
| Cmdr. A. Rivera | Lunar base | Sleep and mood dropping, resting heart rate rising | Watch |
| Eng. L. Moreau | Mars transit (3–22 min delay) | Temperature rising past 38 °C, blood pressure trending up | Critical, Earth-independent mode |

## Earth-independent mode

Inspired by NASA's **Earth-Independent Medical Operations (EIMO)** concept (Human Research Program,
Exploration Medical Capability): the farther a crew is from Earth, the less it can rely on real-time
support from the ground. Houston Pulse gives **the same Critical alert a different response depending on
the distance to Earth**.

**Rule** (`backend/app/analysis/autonomy.py`) — based only on signal physics:

> Earth-independent mode is **active** when `overall_level == "critical"` **and** the signal round trip
> `2 × one_way_delay_s` is longer than `round_trip_threshold_s` (600 s = 10 min).

| Environment | One-way delay | Round trip | Critical alert → |
|---|---|---|---|
| Low Earth orbit (station) | ≈ 1 s (prototype approximation) | ≈ 2 s | contact the flight surgeon now |
| Lunar base | 1.28 s | 2.6 s | contact the flight surgeon now |
| Mars transit, best case | 182 s (3 min) | 6 min | contact the flight surgeon now (not used by the demo) |
| Mars transit, worst case (used) | 1,339 s (22 min) | 45 min | **Earth-independent mode** |

**Signal delays** — one-way delay = distance / speed of light (299,792 km/s), computed by the backend
from the distances in `environments.json`:

| Environment | Distance (NASA NSSDCA) | Calculation |
|---|---|---|
| Lunar base | 384,400 km (Moon semimajor axis, [Moon Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html)) | 384,400 / 299,792 ≈ 1.28 s |
| Mars transit, minimum | 54.6 × 10⁶ km ([Mars Fact Sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html), distance from Earth) | 54.6 × 10⁶ / 299,792 ≈ 182 s ≈ 3 min |
| Mars transit, maximum | 401.4 × 10⁶ km (same sheet) | 401.4 × 10⁶ / 299,792 ≈ 1,339 s ≈ 22 min |
| Low Earth orbit | — | ≈ 1 s, a prototype approximation for relays through ground and satellite networks (not a distance calculation) |

The header, the Earth-independent panel and the report all use these same values (`GET /environments`
and the `autonomy` block), shown as e.g. *22 min one-way (worst case, range 3–22 min)*.

The status endpoint returns an `autonomy` block: `active`, `one_way_delay_s`,
`earliest_reply_s` (= 2 × delay + ground response time) and a readable `reason`.

**Configuration** (`backend/app/config/environments.json`). These are **prototype design choices, not NASA rules**:

| Key | Value | Used for |
|---|---|---|
| `environments.*.distance_km` → one-way delay | 1 s / 1.28 s / 1,339 s | the rule; Mars uses the worst case of its 182–1,339 s range |
| `autonomy.round_trip_threshold_s` | 600 | the rule |
| `autonomy.ground_response_s` | 900 (15 min) | assumed time for the flight surgeon to answer; **only** for `earliest_reply_s` and the countdown, never in the rule |
| `autonomy.tight_check_interval_hours` | 2 | re-measurement interval of the critical indicator(s) in this mode (instead of 24 h) |
| `autonomy.episode_window_hours` | 24 | episode length (see below) |

The frontend reads the environments from `GET /environments`, so the delays are defined in one place.

**What the crew sees when the mode is active**
- Banner *“Earth cannot respond in time — act on board”*, the one-way delay and the earliest possible reply.
- For each critical indicator, 5 onboard steps from `indicators.json` (`autonomy_steps`). They are
  **monitoring and communication steps only** (re-measure to confirm, check related indicators, notify the
  Crew Medical Officer, open the onboard procedure, log symptoms). No diagnosis, no medication, no treatment.
  Each checked step is stored with its time (`AutonomyAction` table).
- Today's checks asks for the critical indicator **every 2 h** and shows the time left before the next measurement.
- **Send report to Earth** stores the sending time (`ReportTransmission` table) and the flight surgeon
  report lists the checked steps with their times; steps checked after the last transmission are marked
  *not yet sent*. The steps included are frozen when the report is sent (`ReportStep` table), so the step
  count and the simulated reply always match what was actually sent. Countdowns: *Reaches Earth in mm:ss*, then *Earliest reply in mm:ss*.
- **Demo speed ×60** (clearly labelled simulation) speeds up the countdown for presentations. When the reply
  time has passed, a **SIMULATED** flight surgeon reply is shown; no real ground link exists.

**Episodes.** To keep it simple, only steps checked and reports sent in the **last 24 hours** count. A step
checked during a past alert therefore never shows as already done during a new one. `python -m scripts.generate_data`
also clears all checked steps and sent reports.

**NASA sources**
- [Earth-Independent Medical Operations (EIMO) Concept of Operations](https://ntrs.nasa.gov/citations/20250000009)
- [Challenges in Communications for Exploration Class Missions](https://ntrs.nasa.gov/citations/20250002660)
- [Clinical Decision Support System for Earth-Independent Medical Operations](https://www.nasa.gov/?p=648602)

Every crew member carries the same standard kit of five **simulated** devices (see [Devices](#devices-simulated)).
Each generated reading is attributed to the device that measures it (`source: "device"`); **mood is self-reported**,
so it stays `source: "simulated"`. The values themselves are identical either way, so the demo story does not change.
The generator prints each device's id and token at the end.

> **Schema change (devices):** the SQLite schema now has a `device` table and a `measurement.device_id` column.
> If you have an older `backend/houston_pulse.db`, delete it and rerun `python -m scripts.generate_data`
> (the generator also drops and recreates the tables itself), then restart the API.

## Structure

```
backend/                       FastAPI + SQLite (Python)
  app/main.py                  app entry point, CORS, routers
  app/models.py                tables: Astronaut, Device, Measurement, AutonomyAction, ReportTransmission, ReportStep
  app/routers/                 REST endpoints
  app/analysis/anomaly.py      baseline + trend + documented thresholds
  app/analysis/checks.py       today's checks (one measurement per indicator per 24 h, 2 h in Earth-independent mode)
  app/analysis/autonomy.py     Earth-independent mode rule
  app/config/indicators.json   labels, explanations, guidance, onboard steps, sources
  app/config/environments.json signal delays and Earth-independent mode parameters
  app/config/thresholds.json   documented reference thresholds (with sources)
  app/config/devices.json      device kinds, indicators each may send, what they are modeled on
  scripts/generate_data.py     simulated demo data (+ simulated devices)
  scripts/device_simulator.py  simulated device sending live heart rate readings
  tests/                       pytest suite (analysis rules + API)
frontend/                      Vue 3 + TypeScript + Vite + Plotly
  src/App.vue                  page layout and headline logic
  src/components/VitalRing.vue ring + body silhouette
  src/components/IndicatorGrid.vue, HistoryChart.vue, MeasurementForm.vue, TodayChecks.vue
  src/components/AutonomyPanel.vue  Earth-independent mode panel (steps, report, countdown)
  src/api.ts, src/types.ts     API client and shared types
```

## Run it

**Backend** — Python 3.10+ (the team uses 3.14; see `backend/.python-version`):
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
python -m pytest -q                  # run the tests
```
On first start the database is empty, so the simulated demo data is generated automatically.
After that, restarts keep everything (including manually logged measurements).

- **Fresh dates before a demo:** `python -m scripts.generate_data` wipes the database and regenerates
  the simulated data ending 1 hour ago (manual entries, checked onboard steps and sent reports are lost).
- **Start with an empty database:** set `HOUSTON_PULSE_NO_SEED=1` to disable the auto-seed
  (e.g. `HOUSTON_PULSE_NO_SEED=1 uvicorn app.main:app --port 8000`).

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
| GET | `/astronauts/{id}/status` | per indicator: `value`, `baseline`, `level`, `trend`, `reasons[]`, `last_source` (`{type, device_name}`), plus `overall_level` and the `autonomy` block |
| GET | `/astronauts/{id}/measurements?indicator=&start=&end=` | history; each row has `source` (`simulated` / `manual` / `device`), `device_id`, `device_name` |
| GET | `/astronauts/{id}/devices` | paired devices: `kind`, `name`, `simulated`, `last_seen`, `status` (`live` < 2 min, `synced` < 24 h, `stale` ≥ 24 h, `never`), `indicators`, `latest` (latest reading this device sent per indicator: `indicator`, `label`, `unit`, `value`, `timestamp`). Never returns the token |
| POST | `/devices/{device_id}/readings` | header `X-Device-Token`; body `{readings: [{indicator, value, timestamp?}]}` (1–100). 401 bad token, 422 if a reading is not supported by the device kind or fails the [input validation](#input-validation) (whole batch rejected). Stored with `source: "device"` |
| GET | `/astronauts/{id}/checks` | today's checks: per indicator `done` (measured in the last 24 h), `last_timestamp`, `hours_since_last`, plus `done_count` / `total`; in Earth-independent mode the critical indicators also have `interval_hours` (2) and `next_due_in_s` |
| POST | `/astronauts/{id}/measurements` | body `{indicator, value, timestamp?}`, stored with `source: "manual"`; 422 if the value fails the [input validation](#input-validation) |
| GET | `/indicators` | metadata, explanations, guidance, onboard steps, sources |
| GET | `/environments` | environments (name, one-way delay, source) and Earth-independent mode parameters |
| GET | `/astronauts/{id}/autonomy` | onboard steps of each critical indicator with `checked_at` and `in_last_report`, plus `report_sent_at`, `report_steps` (frozen at sending) and `new_steps_since_report` (last 24 h only) |
| PUT / DELETE | `/astronauts/{id}/autonomy/actions/{indicator}/{step_index}` | check / uncheck an onboard step |
| POST | `/astronauts/{id}/autonomy/report` | record that a report was sent to Earth now, with the steps checked so far |

## Devices (simulated)

Astronauts don't only type values: on the ISS, the Canadian Space Agency's Bio-Monitor smart shirt records
vital signs, and NASA planned actigraphy wrist monitors for the Artemis II crew. We cannot connect real
hardware, so Houston Pulse implements the real architecture (paired devices, per-device token, readings
endpoint, validation) and demos it with **simulated** devices. **None of them is a real integration**, and
every device name says "(simulated)".

| Kind | May send | Modeled on |
|---|---|---|
| `smart_shirt` | heart rate, systolic blood pressure | CSA Bio-Monitor smart shirt used on the ISS ([CSA](https://www.asc-csa.gc.ca/eng/sciences/bio-monitor.asp)). Its skin temperature is **not** mapped to body temperature: skin temperature is not core body temperature. |
| `actigraphy_band` | sleep | Actigraphy wrist monitors planned for the Artemis II crew, ARCHeR study ([NASA](https://www.nasa.gov/humans-in-space/artemis-ii-crew-to-advance-human-spaceflight-research/)) |
| `bp_cuff` | systolic + diastolic blood pressure | generic automatic blood pressure cuff |
| `thermometer` | body temperature | generic body thermometer |
| `glucometer` | blood glucose | generic blood glucose meter |

The kinds live in `backend/app/config/devices.json`. **Every crew member carries the same standard kit** (all
simulated), and the generated history of each indicator comes from one device:

| Device | Generated history |
|---|---|
| Bio-Monitor shirt (simulated) | heart rate |
| Sleep band (simulated) | sleep |
| BP cuff (simulated) | systolic + diastolic blood pressure (the cuff is the reference; the shirt's systolic is not duplicated) |
| Thermometer (simulated) | body temperature |
| Glucometer (simulated) | blood glucose |
| — | mood: self-reported, no device can measure it |

Device ids follow the crew order, five per person: Rivera 1–5, Tanaka 6–10, Moreau 11–15 (the shirt is the
first of each: 1, 6, 11). Rivera's thermometer and glucometer show "Not synced for 25 h" because her glucose and
temperature checks are due.

**Run the device simulator** (stdlib only) while the API is running:
```bash
cd backend
python -m scripts.generate_data          # prints each device id + token
python -m scripts.device_simulator --device-id 1 --token <token of Rivera's shirt>
python -m scripts.device_simulator --device-id 1 --token <token> --spike   # ramps up to ~110 bpm in ~30 s
```
It sends one heart rate reading every 5 s (`--interval`), with small noise around the latest value, to
`--api` (default `http://localhost:8000`; on Windows, `http://127.0.0.1:8000` avoids a slow IPv6 fallback).
`--spike` crosses the documented AHA threshold (100 bpm) to show a live critical alert. Ctrl+C stops it.

### Demo: live devices

Device status in the UI: **Live** (reading in the last 2 min), **Synced · 1 h ago** (last 24 h),
**Not synced for 26 h** (24 h or more), **Never synced**.

To make the smart shirts stream without running a separate script, start the backend with
`HP_SIMULATE_DEVICES=1`: every 5 s, each `smart_shirt` device sends a **simulated** heart rate (small noise
around its latest value), through the same validation as `POST /devices/{id}/readings`. It is off by default
and always off in tests.

```powershell
# Windows PowerShell, from backend/
$env:HP_SIMULATE_DEVICES = "1"
uvicorn app.main:app --reload --port 8000
Remove-Item Env:HP_SIMULATE_DEVICES   # afterwards, to turn it off for this terminal
```
```bash
# macOS / Linux
HP_SIMULATE_DEVICES=1 uvicorn app.main:app --reload --port 8000
```

To show a critical alert live, use the external simulator with `--spike` on a shirt (see above). Run it with
live mode **off**, otherwise the two sources send heart rates to the same shirt at the same time.

## Input validation

Manual entries are checked before they are stored (`backend/app/validation.py`), and the form checks them
as you type. A value is rejected with HTTP 422 if it is not a finite number, is outside the range below,
does not match the step, or has a timestamp more than 5 minutes in the future.

> **These are plausibility limits for data entry, not medical thresholds.** They only catch typos and
> impossible values (e.g. a heart rate of 720). They never affect the analysis levels, which come only from
> the personal baseline and the documented thresholds in `thresholds.json`.

| Indicator | Allowed range | Step |
|---|---|---|
| Heart rate | 20–250 bpm | 1 |
| Blood pressure (systolic) | 50–260 mmHg | 1 |
| Blood pressure (diastolic) | 30–160 mmHg | 1 |
| Blood glucose | 20–600 mg/dL | 1 |
| Body temperature | 30.0–43.0 °C | 0.1 |
| Sleep | 0–24 h | 0.25 |
| Mood (self-reported) | 1–5 | 1 (whole number) |

The limits live in the `input` object of each indicator in `backend/app/config/indicators.json`, together
with the form's `placeholder` and `help` text (examples for the form, not reference values).
The simulated demo data is rounded to these steps, so it passes the same checks.

## Next steps

Other risks identified by NASA's Human Research Program that Houston Pulse could monitor next:
radiation dose (personal dosimeter), blood oxygen saturation (hypoxia risk), daily exercise
(bone and muscle loss countermeasure), and vision checks (Spaceflight Associated Neuro-ocular Syndrome).
