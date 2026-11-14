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
