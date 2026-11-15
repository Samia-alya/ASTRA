"""Loads the JSON config files."""
import json
from functools import lru_cache
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent


@lru_cache
def indicators() -> dict:
    return json.loads((CONFIG_DIR / "indicators.json").read_text(encoding="utf-8"))


@lru_cache
def thresholds() -> dict:
    data = json.loads((CONFIG_DIR / "thresholds.json").read_text(encoding="utf-8"))
    data.pop("_README", None)
    return data


def _light_time(distance_km: float, c: float) -> float:
    s = distance_km / c
    return round(s, 2) if s < 10 else round(s)


@lru_cache
def environments() -> dict:
    """Environment key -> name, one_way_delay_s, delay_range_s?, source.

    one_way_delay_s = distance_km / speed of light when a distance is given (single source of truth).
    """
    data = json.loads((CONFIG_DIR / "environments.json").read_text(encoding="utf-8"))
    c = data["speed_of_light_km_s"]
    envs = {}
    for key, e in data["environments"].items():
        e = dict(e)
        if "distance_km" in e:
            e["one_way_delay_s"] = _light_time(e["distance_km"], c)
        if "distance_range_km" in e:
            e["delay_range_s"] = [_light_time(d, c) for d in e["distance_range_km"]]
        envs[key] = e
    return envs


def display_value(indicator: str, value: float) -> str:
    """Same rounding as the UI (frontend fmt): whole numbers when the entry step is >= 1, else 1 decimal.
    Half-up on the exact binary value, like JavaScript's toFixed / Math.round for positive values."""
    from decimal import ROUND_HALF_UP, Decimal

    step = indicators().get(indicator, {}).get("input", {}).get("step", 0.1)
    q = Decimal(1) if step >= 1 else Decimal("0.1")
    return str(Decimal(value).quantize(q, rounding=ROUND_HALF_UP))


@lru_cache
def autonomy_rule() -> dict:
    """Earth-independent mode parameters (prototype design choices, not NASA rules)."""
    data = json.loads((CONFIG_DIR / "environments.json").read_text(encoding="utf-8"))["autonomy"]
    return {k: v for k, v in data.items() if not k.startswith("_")}
