"""Cross-indicator rules and readiness (owner: Member 1).

A single indicator slightly off is noise. Several weak signals pointing the
same way are worth an explained alert. Rule parameters, wording, suggested
actions and sources live in config/correlation_rules.json.

The combinations are team hypotheses built on cited findings, not clinically
validated rules; every alert says so. A rule never raises "critical".
"""
from __future__ import annotations

import pandas as pd

from app.analysis.anomaly import IndicatorStatus
from app.config import correlation_rules, indicators


def _mean_last(frames: dict[str, pd.DataFrame], key: str, n: int) -> float | None:
    df = frames.get(key)
    if df is None or len(df) < n:
        return None
    return float(df.sort_values("timestamp")["value"].tail(n).mean())


def _worse(st: IndicatorStatus | None) -> bool:
    return st is not None and st.level in ("attention", "critical")


def _alert(key: str, evidence: list[str]) -> dict:
    rule = correlation_rules()[key]
    return {
        "rule": key,
        "title": rule["title"],
        "level": "attention",
        "indicators": rule.get("indicators", []),
        "blocks_critical_ops": rule["blocks_critical_ops"],
        "explanation": rule["explanation"],
        "evidence": evidence,
        "actions": rule["actions"],
        "sources": rule["sources"],
        "validation": "Team hypothesis built on the cited findings. Not clinically validated.",
    }


def evaluate(statuses: dict[str, IndicatorStatus], frames: dict[str, pd.DataFrame]) -> list[dict]:
    """statuses: indicator -> space-mode status. frames: indicator -> [timestamp, value]."""
    rules = correlation_rules()
    alerts: list[dict] = []
    get = statuses.get

    # --- Masked fatigue: short sleep + worse reaction test + "I feel fine" ---
    p = rules["masked_fatigue"]["params"]
    sleep = _mean_last(frames, "sleep_hours", p["sleep_nights"])
    alert_st, lapses, rt = get("alertness"), get("pvt_lapses"), get("pvt_mean_rt")
    objective_worse = (_worse(lapses) and (lapses.deviation_pct or 0) > 0) \
        or (_worse(rt) and (rt.deviation_pct or 0) > 0)
    if sleep is not None and sleep < p["sleep_mean_below_h"] and objective_worse \
            and alert_st is not None and alert_st.value is not None \
            and alert_st.value >= p["alertness_at_least"]:
        ev = [f"Sleep: {sleep:.1f} h on average over the last {p['sleep_nights']} nights."]
        if lapses is not None and lapses.value is not None:
            ev.append(f"Reaction test: {lapses.value:g} lapses (your baseline: "
                      f"{lapses.baseline if lapses.baseline is not None else 'n/a'}).")
        if rt is not None and rt.value is not None:
            ev.append(f"Mean reaction time: {rt.value:g} ms (your baseline: "
                      f"{rt.baseline if rt.baseline is not None else 'n/a'} ms).")
        ev.append(f"Self-rated alertness: {alert_st.value:g}/10.")
        alerts.append(_alert("masked_fatigue", ev))

    # --- Fever beyond adaptation + faster heart rate ---
    p = rules["fever_beyond_adaptation"]["params"]
    temp, hr = get("temperature"), get("heart_rate")
    if _worse(temp) and temp.baseline is not None and temp.value > temp.baseline \
            and hr is not None and (hr.deviation_pct or 0) >= p["heart_rate_rise_pct"]:
        alerts.append(_alert("fever_beyond_adaptation", [
            f"Temperature: {temp.value:g} °C, {temp.value - temp.baseline:+.1f} °C vs your "
            f"space-adapted baseline ({temp.baseline:g} °C).",
            f"Resting heart rate: {hr.value:g} bpm ({hr.deviation_pct:+.0f}% vs your baseline).",
        ]))

    # --- Sustained stress load: short sleep + lower mood + faster heart rate ---
    p = rules["sustained_stress_load"]["params"]
    sleep = _mean_last(frames, "sleep_hours", p["sleep_nights"])
    mood = get("mood")
    if sleep is not None and sleep < p["sleep_mean_below_h"] \
            and mood is not None and (mood.deviation_pct or 0) < 0 and _worse(mood) \
            and hr is not None and (hr.deviation_pct or 0) >= p["heart_rate_rise_pct"]:
        alerts.append(_alert("sustained_stress_load", [
            f"Sleep: {sleep:.1f} h on average over the last {p['sleep_nights']} nights.",
            f"Mood: {mood.value:g}/5 (your baseline: {mood.baseline}).",
            f"Resting heart rate: {hr.value:g} bpm ({hr.deviation_pct:+.0f}% vs your baseline).",
        ]))
    return alerts


def readiness(statuses: dict[str, IndicatorStatus], alerts: list[dict]) -> dict:
    """GO / CAUTION / NO-GO for critical operations. A decision AID: the
    crew and flight surgeon decide. Deliberately a transparent rule, not a score."""
    reasons: list[str] = []
    critical = [s for s in statuses.values() if s.level == "critical"]
    blocking = [a for a in alerts if a["blocks_critical_ops"]]
    attention = [s for s in statuses.values() if s.level == "attention"]
    if critical or blocking:
        reasons += [f"{indicators().get(s.indicator, {}).get('label', s.indicator)}: critical limit crossed."
                    for s in critical]
        reasons += [a["title"] for a in blocking]
        return {"status": "NO_GO", "label": "NO-GO for critical operations", "reasons": reasons}
    if attention or alerts:
        reasons += [a["title"] for a in alerts]
        reasons.append(f"{len(attention)} indicator(s) need attention.")
        return {"status": "CAUTION", "label": "CAUTION: review before critical operations",
                "reasons": reasons}
    return {"status": "GO", "label": "GO for critical operations",
            "reasons": ["All indicators within your space-adapted range."]}
