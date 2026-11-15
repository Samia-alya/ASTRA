"""Loads the JSON config files."""
import json
from functools import lru_cache
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent


def _load(name: str) -> dict:
    data = json.loads((CONFIG_DIR / name).read_text(encoding="utf-8"))
    data.pop("_README", None)
    return data


@lru_cache
def indicators() -> dict:
    return _load("indicators.json")


@lru_cache
def thresholds() -> dict:
    return _load("thresholds.json")


@lru_cache
def space_adaptation() -> dict:
    """Expected normal in-flight change per indicator (sourced)."""
    return _load("space_adaptation.json")


@lru_cache
def correlation_rules() -> dict:
    return _load("correlation_rules.json")


@lru_cache
def environments() -> dict:
    return _load("environments.json")
