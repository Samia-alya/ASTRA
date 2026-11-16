"""API tests on a temporary database filled with the simulated data.

Run from backend/:  python -m pytest -q
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine

import app.database as database
from app.main import app
from app.validation import validate_value

# The `client` fixture (temporary database + simulated data) lives in conftest.py.


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_astronauts_and_demo_levels(client):
    astronauts = client.get("/astronauts").json()
    assert len(astronauts) == 3
    levels = {a["name"]: client.get(f"/astronauts/{a['id']}/status").json()["overall_level"] for a in astronauts}
    # Demo story: one steady, one to watch, one critical.
    assert sorted(levels.values()) == ["attention", "critical", "normal"]


def test_status_shape(client):
    body = client.get("/astronauts/1/status").json()
    assert body["disclaimer"]
    first = body["indicators"][0]
    for key in ("indicator", "label", "unit", "body_zone", "value", "baseline", "level", "trend", "reasons"):
        assert key in first


def test_indicators_have_guidance(client):
    meta = client.get("/indicators").json()
    for key, m in meta.items():
        assert {"normal", "attention", "critical"} <= set(m["guidance"]), key


def test_add_measurement_becomes_latest(client):
    r = client.post("/astronauts/2/measurements", json={"indicator": "heart_rate", "value": 120})
    assert r.status_code == 201 and r.json()["source"] == "manual"
    hr = next(i for i in client.get("/astronauts/2/status").json()["indicators"] if i["indicator"] == "heart_rate")
    # Above the AHA normal resting range: Watch, not an emergency.
    assert hr["value"] == 120 and hr["level"] == "attention"
    assert any("normal resting range" in r for r in hr["reasons"])
    # A hypertensive crisis value is still critical.
    client.post("/astronauts/2/measurements", json={"indicator": "bp_systolic", "value": 185})
    sbp = next(i for i in client.get("/astronauts/2/status").json()["indicators"] if i["indicator"] == "bp_systolic")
    assert sbp["level"] == "critical"


def test_validation_errors(client):
    assert client.post("/astronauts/2/measurements", json={"indicator": "nope", "value": 1}).status_code == 422
    assert client.post("/astronauts/2/measurements", json={"indicator": "mood"}).status_code == 422
    assert client.get("/astronauts/999/status").status_code == 404


def _due(client, astronaut_id):
    body = client.get(f"/astronauts/{astronaut_id}/checks").json()
    return body, {i["indicator"] for i in body["items"] if not i["done"]}


def test_checks_rivera_has_two_due(client):
    body, due = _due(client, 1)
    assert due == {"glucose", "temperature"}
    assert body["total"] == 7 and body["done_count"] == 5
    item = next(i for i in body["items"] if i["indicator"] == "glucose")
    assert set(item) == {"indicator", "label", "unit", "done", "last_timestamp", "hours_since_last"}
    assert item["hours_since_last"] > 24


def test_checks_tanaka_all_done(client):
    body, due = _due(client, 2)
    assert due == set() and body["done_count"] == body["total"] == 7


def test_checks_logging_marks_done(client):
    assert client.post("/astronauts/1/measurements", json={"indicator": "glucose", "value": 95}).status_code == 201
    _, due = _due(client, 1)
    assert due == {"temperature"}


def test_checks_unknown_astronaut(client):
    assert client.get("/astronauts/999/checks").status_code == 404


def test_rivera_still_attention_on_scenario(client):
    levels = {i["indicator"]: i["level"] for i in client.get("/astronauts/1/status").json()["indicators"]}
    assert levels["sleep_hours"] == levels["mood"] == levels["heart_rate"] == "attention"


# --- Plausibility validation (data-entry limits, NOT medical thresholds) ---

VALID = {"heart_rate": 72, "bp_systolic": 120, "bp_diastolic": 80, "glucose": 95,
         "temperature": 36.8, "sleep_hours": 7.25, "mood": 4}


def _post(client, indicator, value, **extra):
    return client.post("/astronauts/2/measurements", json={"indicator": indicator, "value": value, **extra})


@pytest.mark.parametrize("indicator,value", VALID.items())
def test_valid_value_accepted(client, indicator, value):
    assert _post(client, indicator, value).status_code == 201


@pytest.mark.parametrize("indicator,value,message", [
    ("heart_rate", 720, "Heart rate must be between 20 and 250 bpm."),
    ("temperature", 50, "Body temperature must be between 30.0 and 43.0 °C."),
    ("mood", 6, "Mood (self-reported) must be between 1 and 5."),
    ("mood", 3.5, "Mood (self-reported) must be a whole number."),
    ("sleep_hours", 25, "Sleep must be between 0 and 24 h."),
    ("sleep_hours", 7.3, "Sleep must be in steps of 0.25 h."),
])
def test_implausible_value_rejected(client, indicator, value, message):
    r = _post(client, indicator, value)
    assert r.status_code == 422 and r.json()["detail"] == message


def test_limits_are_inclusive_and_float_tolerant(client):
    assert _post(client, "temperature", 43.0).status_code == 201
    assert _post(client, "temperature", 36.6).status_code == 201  # 36.6 is not exact in binary
    assert _post(client, "sleep_hours", 0).status_code == 201


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_value_rejected(client, raw):
    r = client.post("/astronauts/2/measurements", content='{"indicator": "heart_rate", "value": %s}' % raw,
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_future_timestamp_rejected(client):
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    r = _post(client, "heart_rate", 72, timestamp=future)
    assert r.status_code == 422 and "future" in r.json()["detail"]
    soon = (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat()
    assert _post(client, "heart_rate", 72, timestamp=soon).status_code == 201


def test_generated_demo_data_is_plausible(client):
    meta = client.get("/indicators").json()
    for a in client.get("/astronauts").json():
        for m in client.get(f"/astronauts/{a['id']}/measurements").json():
            assert validate_value(meta[m["indicator"]], m["value"]) is None, m


# --- Auto-seed at startup -------------------------------------------------------

@pytest.fixture()
def empty_engine(tmp_path, monkeypatch):
    """A fresh, empty database (tables created by the app's lifespan)."""
    monkeypatch.delenv("HOUSTON_PULSE_NO_SEED", raising=False)
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(database, "engine", engine)
    return engine


def test_startup_seeds_empty_database(empty_engine):
    with TestClient(app) as c:
        assert len(c.get("/astronauts").json()) == 3
        assert c.get("/astronauts/1/measurements").json()


def test_startup_keeps_existing_data(empty_engine):
    with TestClient(app) as c:
        r = c.post("/astronauts/2/measurements", json={"indicator": "heart_rate", "value": 71})
        assert r.status_code == 201
        before = c.get("/astronauts/2/measurements").json()
    # Restart: existing data, including the manual entry, must survive unchanged.
    with TestClient(app) as c:
        after = c.get("/astronauts/2/measurements").json()
        assert len(c.get("/astronauts").json()) == 3
    assert after == before
    assert any(m["source"] == "manual" and m["value"] == 71 for m in after)


def test_startup_seed_disabled_by_env(empty_engine, monkeypatch):
    monkeypatch.setenv("HOUSTON_PULSE_NO_SEED", "1")
    with TestClient(app) as c:
        assert c.get("/astronauts").json() == []
