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


@lru_cache
def environments() -> dict:
    """Environment key -> name, one_way_delay_s, delay_range_s?, source."""
    return json.loads((CONFIG_DIR / "environments.json").read_text(encoding="utf-8"))["environments"]


@lru_cache
def autonomy_rule() -> dict:
    """Earth-independent mode parameters (prototype design choices, not NASA rules)."""
    data = json.loads((CONFIG_DIR / "environments.json").read_text(encoding="utf-8"))["autonomy"]
    return {k: v for k, v in data.items() if not k.startswith("_")}
