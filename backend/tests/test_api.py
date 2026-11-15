"""API tests on a temporary database filled with the simulated data.

Run from backend/:  python -m pytest -q
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine

import app.database as database
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(database, "engine", engine)
    import scripts.generate_data as gen
    monkeypatch.setattr(gen, "engine", engine)
    SQLModel.metadata.create_all(engine)
    gen.main()
    with TestClient(app) as c:
        yield c


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
    assert hr["value"] == 120 and hr["level"] == "critical"


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
