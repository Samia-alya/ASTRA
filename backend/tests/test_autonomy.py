"""Tests for the Earth-independent mode (app/analysis/autonomy.py + autonomy endpoints).

Run from backend/:  python -m pytest -q
"""
from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.analysis.autonomy import autonomy_state
from app.analysis.checks import compute_checks
from app.config import autonomy_rule, environments, indicators
from app.models import AutonomyAction, ReportStep, ReportTransmission
from tests.test_api import client  # noqa: F401  (fixture)

RIVERA, TANAKA, MOREAU = 1, 2, 3


# --- Switch rule (pure function) ---------------------------------------------------

def test_station_critical_is_not_autonomous():
    a = autonomy_state("critical", "station")
    assert a["active"] is False
    assert "contact your flight surgeon now" in a["reason"]


def test_lunar_critical_is_not_autonomous():
    a = autonomy_state("critical", "lunar_base")
    assert a["active"] is False and a["one_way_delay_s"] == 1.28


def test_mars_critical_is_autonomous():
    a = autonomy_state("critical", "mars_transit")
    assert a["active"] is True
    assert a["one_way_delay_s"] == 1339
    assert a["earliest_reply_s"] == 2 * 1339 + autonomy_rule()["ground_response_s"]
    assert "onboard monitoring steps" in a["reason"]


def test_mars_not_critical_is_not_autonomous():
    for level in ("attention", "normal", "no_data"):
        assert autonomy_state(level, "mars_transit")["active"] is False


def test_rule_uses_round_trip_only(monkeypatch):
    """Mars best case (3 min one-way = 6 min round trip) stays under the 10 min threshold,
    even though earliest_reply_s (with ground response) is above it."""
    best = dict(environments()["mars_transit"], one_way_delay_s=environments()["mars_transit"]["delay_range_s"][0])
    monkeypatch.setitem(environments(), "mars_transit", best)
    a = autonomy_state("critical", "mars_transit")
    assert a["active"] is False and a["earliest_reply_s"] > autonomy_rule()["round_trip_threshold_s"]


def test_delays_are_distance_over_speed_of_light():
    """NSSDCA fact sheets: Moon semimajor axis 384,400 km; Mars 54.6-401.4 million km from Earth."""
    envs = environments()
    assert envs["lunar_base"]["one_way_delay_s"] == round(384_400 / 299_792, 2) == 1.28
    assert envs["mars_transit"]["delay_range_s"] == [round(54.6e6 / 299_792), round(401.4e6 / 299_792)]
    assert envs["mars_transit"]["one_way_delay_s"] == envs["mars_transit"]["delay_range_s"][1]
    assert envs["station"]["one_way_delay_s"] == 1  # prototype approximation


def test_unknown_environment_is_not_autonomous():
    assert autonomy_state("critical", "somewhere")["active"] is False


def test_every_critical_indicator_has_monitoring_steps():
    from app.config import thresholds
    for key, t in thresholds().items():
        if t.get("critical_low") is not None or t.get("critical_high") is not None:
            assert 3 <= len(indicators()[key]["autonomy_steps"]) <= 5, key


# --- Status API on the demo data ---------------------------------------------------

def test_demo_crew_autonomy(client):
    active = {a["name"]: client.get(f"/astronauts/{a['id']}/status").json()["autonomy"]["active"]
              for a in client.get("/astronauts").json()}
    assert active == {"Cmdr. A. Rivera": False, "Dr. K. Tanaka": False, "Eng. L. Moreau": True}


def test_tanaka_fever_on_station_contacts_flight_surgeon(client):
    assert client.post(f"/astronauts/{TANAKA}/measurements",
                       json={"indicator": "temperature", "value": 38.4}).status_code == 201
    body = client.get(f"/astronauts/{TANAKA}/status").json()
    assert body["overall_level"] == "critical"
    assert body["autonomy"]["active"] is False
    assert "contact your flight surgeon now" in body["autonomy"]["reason"]


def test_environments_endpoint(client):
    body = client.get("/environments").json()
    assert body["environments"]["mars_transit"]["one_way_delay_s"] == 1339
    assert body["environments"]["mars_transit"]["delay_range_s"] == [182, 1339]
    assert body["autonomy"]["round_trip_threshold_s"] == 600


# --- Onboard steps --------------------------------------------------------------------

def _steps(client, astronaut_id=MOREAU):
    return client.get(f"/astronauts/{astronaut_id}/autonomy").json()


def test_autonomy_lists_steps_for_critical_indicators(client):
    body = _steps(client)
    assert body["autonomy"]["active"] is True
    temp = next(g for g in body["groups"] if g["indicator"] == "temperature")
    assert len(temp["steps"]) == 5 and all(s["checked_at"] is None for s in temp["steps"])
    assert body["report_sent_at"] is None


def test_check_and_uncheck_step(client):
    r = client.put(f"/astronauts/{MOREAU}/autonomy/actions/temperature/0")
    assert r.status_code == 200
    first = r.json()["checked_at"]
    # Idempotent: checking again keeps the original time.
    assert client.put(f"/astronauts/{MOREAU}/autonomy/actions/temperature/0").json()["checked_at"] == first
    temp = next(g for g in _steps(client)["groups"] if g["indicator"] == "temperature")
    assert temp["steps"][0]["checked_at"] == first and temp["steps"][1]["checked_at"] is None

    assert client.delete(f"/astronauts/{MOREAU}/autonomy/actions/temperature/0").status_code == 204
    temp = next(g for g in _steps(client)["groups"] if g["indicator"] == "temperature")
    assert temp["steps"][0]["checked_at"] is None


def test_check_step_validation(client):
    assert client.put(f"/astronauts/{MOREAU}/autonomy/actions/temperature/99").status_code == 404
    assert client.put(f"/astronauts/{MOREAU}/autonomy/actions/mood/0").status_code == 404
    assert client.put("/astronauts/999/autonomy/actions/temperature/0").status_code == 404


def test_send_report_is_persisted(client):
    r = client.post(f"/astronauts/{MOREAU}/autonomy/report")
    assert r.status_code == 201
    sent = datetime.fromisoformat(r.json()["report_sent_at"])
    assert abs((datetime.now(timezone.utc) - sent).total_seconds()) < 10
    assert _steps(client)["report_sent_at"] == r.json()["report_sent_at"]
    assert client.post("/astronauts/999/autonomy/report").status_code == 404


def test_report_freezes_included_steps(client):
    """Steps checked after the last report are not counted as sent (reply + step count use the snapshot)."""
    client.put(f"/astronauts/{MOREAU}/autonomy/actions/temperature/0")
    client.put(f"/astronauts/{MOREAU}/autonomy/actions/temperature/1")
    r = client.post(f"/astronauts/{MOREAU}/autonomy/report").json()
    assert r["included_steps"] == 2
    # Two more steps after sending.
    client.put(f"/astronauts/{MOREAU}/autonomy/actions/temperature/2")
    client.put(f"/astronauts/{MOREAU}/autonomy/actions/temperature/3")
    body = _steps(client)
    assert len(body["report_steps"]) == 2
    assert {s["step_index"] for s in body["report_steps"]} == {0, 1}
    assert body["new_steps_since_report"] == 2
    temp = next(g for g in body["groups"] if g["indicator"] == "temperature")
    assert [s["in_last_report"] for s in temp["steps"]] == [True, True, False, False, False]

    # Unchecking a sent step does not change what the report contained.
    client.delete(f"/astronauts/{MOREAU}/autonomy/actions/temperature/0")
    body = _steps(client)
    assert len(body["report_steps"]) == 2 and body["new_steps_since_report"] == 2
    # Re-checking it later is a new action, not yet sent.
    client.put(f"/astronauts/{MOREAU}/autonomy/actions/temperature/0")
    assert _steps(client)["new_steps_since_report"] == 3

    # A new report includes everything checked so far.
    assert client.post(f"/astronauts/{MOREAU}/autonomy/report").json()["included_steps"] == 4
    body = _steps(client)
    assert len(body["report_steps"]) == 4 and body["new_steps_since_report"] == 0


def test_no_report_yet_has_no_new_steps_count(client):
    client.put(f"/astronauts/{MOREAU}/autonomy/actions/temperature/0")
    body = _steps(client)
    assert body["report_sent_at"] is None and body["report_steps"] == [] and body["new_steps_since_report"] == 0


def test_old_episode_is_ignored(client):
    """A step checked or a report sent more than 24 h ago belongs to a past alert."""
    import app.database as database
    old = datetime.now(timezone.utc) - timedelta(hours=25)
    with Session(database.engine) as s:
        s.add(AutonomyAction(astronaut_id=MOREAU, indicator="temperature", step_index=0, timestamp=old))
        s.add(ReportTransmission(astronaut_id=MOREAU, sent_at=old))
        s.commit()
    body = _steps(client)
    temp = next(g for g in body["groups"] if g["indicator"] == "temperature")
    assert temp["steps"][0]["checked_at"] is None and body["report_sent_at"] is None
    # Checking it again in the new episode gets a fresh time.
    fresh = datetime.fromisoformat(client.put(f"/astronauts/{MOREAU}/autonomy/actions/temperature/0").json()["checked_at"])
    assert fresh > old + timedelta(hours=24)


def test_seed_clears_actions_and_reports(client):
    import app.database as database
    import scripts.generate_data as gen
    client.put(f"/astronauts/{MOREAU}/autonomy/actions/temperature/0")
    client.post(f"/astronauts/{MOREAU}/autonomy/report")
    gen.seed(database.engine)
    with Session(database.engine) as s:
        from sqlmodel import select
        assert s.exec(select(AutonomyAction)).all() == []
        assert s.exec(select(ReportTransmission)).all() == []
        assert s.exec(select(ReportStep)).all() == []


# --- Tighter monitoring ------------------------------------------------------------

NOW = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)
META = {"temperature": {"label": "Body temperature", "unit": "°C"},
        "sleep_hours": {"label": "Sleep", "unit": "h"}}


def test_checks_tight_interval_two_hours():
    latest = {"temperature": NOW - timedelta(hours=3), "sleep_hours": NOW - timedelta(hours=3)}
    items = {i["indicator"]: i for i in compute_checks(latest, META, now=NOW, tight={"temperature"})["items"]}
    assert items["temperature"]["done"] is False and items["temperature"]["interval_hours"] == 2
    assert items["temperature"]["next_due_in_s"] == 0
    assert items["sleep_hours"]["done"] is True and "interval_hours" not in items["sleep_hours"]


def test_checks_tight_next_due():
    latest = {"temperature": NOW - timedelta(minutes=30)}
    item = compute_checks(latest, META, now=NOW, tight={"temperature"})["items"][0]
    assert item["done"] is True and item["next_due_in_s"] == 90 * 60


def test_checks_default_unchanged():
    latest = {"temperature": NOW - timedelta(hours=3)}
    item = compute_checks(latest, META, now=NOW)["items"][0]
    assert item["done"] is True and set(item) == {
        "indicator", "label", "unit", "done", "last_timestamp", "hours_since_last"}


def test_checks_api_moreau_temperature_every_two_hours(client):
    items = {i["indicator"]: i for i in client.get(f"/astronauts/{MOREAU}/checks").json()["items"]}
    temp = items["temperature"]
    assert temp["interval_hours"] == 2
    # Last simulated point is 1 h ago: done, next due in about 1 h.
    assert temp["done"] is True and 0 < temp["next_due_in_s"] <= 3600
    assert "interval_hours" not in items["sleep_hours"]
    # Tanaka (station) keeps the 24 h routine.
    tanaka = client.get(f"/astronauts/{TANAKA}/checks").json()["items"]
    assert all("interval_hours" not in i for i in tanaka)
