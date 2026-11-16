"""Device integration tests. All devices are SIMULATED."""
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

import app.database as database
from app.config import devices, indicators
from app.live_devices import tick
from app.models import Device
from app.routers.astronauts import device_status


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
    assert [d["name"] for d in body] == [
        "Bio-Monitor shirt (simulated)", "Sleep band (simulated)", "BP cuff (simulated)",
        "Thermometer (simulated)", "Glucometer (simulated)",
    ]
    for d in body:
        assert "token" not in d and d["simulated"] is True and "(simulated)" in d["name"]
        assert d["last_seen"]  # generated history is attributed to the devices
    # Last reading ~1 h ago -> synced; Rivera's glucometer and thermometer missed today (checks due) -> stale.
    assert {d["kind"]: d["status"] for d in body} == {
        "smart_shirt": "synced", "actigraphy_band": "synced", "bp_cuff": "synced",
        "thermometer": "stale", "glucometer": "stale",
    }
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
    assert listed["status"] == "live" and listed["last_seen"]
    assert {r["indicator"]: r["value"] for r in listed["latest"]} == {"heart_rate": 71, "bp_systolic": 121}

    hr = next(i for i in client.get("/astronauts/1/status").json()["indicators"] if i["indicator"] == "heart_rate")
    assert hr["value"] == 71
    assert hr["last_source"] == {"type": "device", "device_name": "Bio-Monitor shirt (simulated)"}


def test_last_source_for_simulated_and_manual(client):
    # Tanaka: sleep from the sleep band, both blood pressures from the cuff, the rest plain simulated.
    by_ind = {i["indicator"]: i["last_source"] for i in client.get("/astronauts/2/status").json()["indicators"]}
    assert by_ind["sleep_hours"] == {"type": "device", "device_name": "Sleep band (simulated)"}
    assert by_ind["bp_systolic"] == by_ind["bp_diastolic"] == {"type": "device", "device_name": "BP cuff (simulated)"}
    assert by_ind["glucose"] == {"type": "device", "device_name": "Glucometer (simulated)"}
    assert by_ind["mood"] == {"type": "simulated", "device_name": None}  # self-reported
    client.post("/astronauts/2/measurements", json={"indicator": "mood", "value": 4})
    mood = next(i for i in client.get("/astronauts/2/status").json()["indicators"] if i["indicator"] == "mood")
    assert mood["last_source"] == {"type": "manual", "device_name": None}


def test_generator_attributes_history_to_devices(client):
    hr = client.get("/astronauts/1/measurements?indicator=heart_rate").json()
    assert len(hr) == 87 and all(m["source"] == "device" and m["device_name"] == "Bio-Monitor shirt (simulated)" for m in hr)
    sleep = client.get("/astronauts/1/measurements?indicator=sleep_hours").json()
    assert all(m["device_name"] == "Sleep band (simulated)" for m in sleep)
    sys_bp = client.get("/astronauts/1/measurements?indicator=bp_systolic").json()
    assert all(m["device_name"] == "BP cuff (simulated)" for m in sys_bp)  # the cuff, not the shirt
    mood = client.get("/astronauts/1/measurements?indicator=mood").json()
    assert all(m["source"] == "simulated" and m["device_id"] is None for m in mood)
    # Each device: latest value per supported indicator, and last_seen = its latest reading.
    shirt = client.get("/astronauts/1/devices").json()[0]
    assert [r["indicator"] for r in shirt["latest"]] == ["heart_rate"]
    assert shirt["last_seen"] == max(r["timestamp"] for r in shirt["latest"])


def test_device_status_thresholds():
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    assert device_status(None, now) == "never"
    assert device_status(now - timedelta(seconds=30), now) == "live"
    assert device_status(now - timedelta(hours=1), now) == "synced"
    assert device_status(now - timedelta(hours=26), now) == "stale"


def test_live_mode_tick_streams_shirt_heart_rate(client):
    def heart_rates(astro):
        return client.get(f"/astronauts/{astro}/measurements?indicator=heart_rate").json()

    before = {astro: len(heart_rates(astro)) for astro in (1, 3)}  # Rivera and Moreau wear a shirt
    tick({})
    for astro in (1, 3):
        shirt = _device(astro, "smart_shirt")
        rows = heart_rates(astro)
        assert len(rows) == before[astro] + 1
        assert rows[-1]["source"] == "device" and rows[-1]["device_id"] == shirt.id
        listed = next(d for d in client.get(f"/astronauts/{astro}/devices").json() if d["id"] == shirt.id)
        assert listed["status"] == "live"
    # Other device kinds do not stream.
    band = next(d for d in client.get("/astronauts/1/devices").json() if d["kind"] == "actigraphy_band")
    assert band["status"] == "synced"


def test_standard_kit_mapping_is_consistent():
    from scripts.generate_data import GENERATED_BY, KIT
    kinds = {k for k, _ in KIT}
    for ind, kind in GENERATED_BY.items():
        assert kind in kinds and ind in devices()[kind]["indicators"], (ind, kind)
    assert "mood" not in GENERATED_BY  # self-reported: no device measures it
    assert all("(simulated)" in name for _, name in KIT)
