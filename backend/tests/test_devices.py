"""Device integration tests. All devices are SIMULATED."""
from sqlmodel import Session, select

import app.database as database
from app.config import devices, indicators
from app.models import Device


def _device(astronaut_id: int, kind: str) -> Device:
    with Session(database.engine) as s:
        return s.exec(select(Device).where(Device.astronaut_id == astronaut_id, Device.kind == kind)).one()


def _post(client, device: Device, readings, token=None):
    headers = {} if token is False else {"X-Device-Token": token or device.token}
    return client.post(f"/devices/{device.id}/readings", json={"readings": readings}, headers=headers)


def test_device_kinds_only_use_known_indicators():
    for kind, d in devices().items():
        assert set(d["indicators"]) <= set(indicators()), kind
    # Skin temperature is not core body temperature: the shirt must never send it.
    assert "temperature" not in devices()["smart_shirt"]["indicators"]


def test_device_list_hides_tokens(client):
    body = client.get("/astronauts/1/devices").json()
    assert [d["name"] for d in body] == ["Bio-Monitor shirt (simulated)", "Sleep band (simulated)"]
    for d in body:
        assert "token" not in d and d["simulated"] is True and "(simulated)" in d["name"]
        assert d["status"] == "offline" and d["last_seen"] is None
    assert body[0]["indicators"] == ["heart_rate", "bp_systolic"]
    assert client.get("/astronauts/999/devices").status_code == 404


def test_wrong_or_missing_token_is_401(client):
    shirt = _device(1, "smart_shirt")
    assert _post(client, shirt, [{"indicator": "heart_rate", "value": 70}], token="wrong").status_code == 401
    assert _post(client, shirt, [{"indicator": "heart_rate", "value": 70}], token=False).status_code == 401
    other = _device(3, "smart_shirt")  # a valid token, but for another device
    assert _post(client, shirt, [{"indicator": "heart_rate", "value": 70}], token=other.token).status_code == 401


def test_unsupported_indicator_is_422(client):
    shirt = _device(1, "smart_shirt")
    r = _post(client, shirt, [{"indicator": "temperature", "value": 36.8}])
    assert r.status_code == 422 and "cannot send 'temperature'" in r.json()["detail"]


def test_implausible_value_is_422_and_batch_is_atomic(client):
    shirt = _device(1, "smart_shirt")
    before = len(client.get("/astronauts/1/measurements?indicator=heart_rate").json())
    r = _post(client, shirt, [{"indicator": "heart_rate", "value": 70}, {"indicator": "heart_rate", "value": 720}])
    assert r.status_code == 422
    assert r.json()["detail"] == "Reading 2: Heart rate must be between 20 and 250 bpm."
    assert len(client.get("/astronauts/1/measurements?indicator=heart_rate").json()) == before


def test_batch_limit(client):
    shirt = _device(1, "smart_shirt")
    assert _post(client, shirt, [{"indicator": "heart_rate", "value": 70}] * 101).status_code == 422
    assert _post(client, shirt, []).status_code == 422


def test_valid_readings_are_stored_as_device(client):
    shirt = _device(1, "smart_shirt")
    r = _post(client, shirt, [{"indicator": "heart_rate", "value": 71}, {"indicator": "bp_systolic", "value": 121}])
    assert r.status_code == 201 and r.json()["stored"] == 2

    latest = client.get("/astronauts/1/measurements?indicator=heart_rate").json()[-1]
    assert latest["value"] == 71 and latest["source"] == "device"
    assert latest["device_id"] == shirt.id and latest["device_name"] == "Bio-Monitor shirt (simulated)"

    listed = next(d for d in client.get("/astronauts/1/devices").json() if d["id"] == shirt.id)
    assert listed["status"] == "online" and listed["last_seen"]

    hr = next(i for i in client.get("/astronauts/1/status").json()["indicators"] if i["indicator"] == "heart_rate")
    assert hr["value"] == 71
    assert hr["last_source"] == {"type": "device", "device_name": "Bio-Monitor shirt (simulated)"}


def test_last_source_for_simulated_and_manual(client):
    status = client.get("/astronauts/2/status").json()
    assert all(i["last_source"] == {"type": "simulated", "device_name": None} for i in status["indicators"])
    client.post("/astronauts/2/measurements", json={"indicator": "mood", "value": 4})
    mood = next(i for i in client.get("/astronauts/2/status").json()["indicators"] if i["indicator"] == "mood")
    assert mood["last_source"] == {"type": "manual", "device_name": None}
