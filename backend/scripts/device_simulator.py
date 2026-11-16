"""SIMULATED device: sends heart rate readings to the running API, like a smart shirt would.

This is NOT a real device integration. It exercises the real device endpoint
(POST /devices/{id}/readings with X-Device-Token) using made-up values: small random
noise around the astronaut's latest heart rate. Standard library only.

Usage (from backend/, with the API running):
    python -m scripts.device_simulator --device-id 1 --token <token printed by generate_data>
    python -m scripts.device_simulator --device-id 6 --token <token> --spike   # Tanaka's shirt: ~110 bpm -> Watch

Ctrl+C stops it.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request

INDICATOR = "heart_rate"
SPIKE_TARGET = 110.0  # bpm, above the AHA normal resting range (100): shows a live Watch alert
SPIKE_SECONDS = 30.0
NOISE_BPM = 1.5
DEFAULT_BASE = 65.0  # only used if the astronaut has no heart rate yet


def _request(method: str, url: str, body: dict | None = None, token: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-Device-Token", token)
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read().decode() or "null")


def _error_detail(e: urllib.error.HTTPError) -> str:
    try:
        return json.loads(e.read().decode()).get("detail", "")
    except Exception:
        return ""


def find_device(api: str, device_id: int) -> tuple[int, dict]:
    """Find which astronaut the device belongs to, using the public endpoints."""
    for astro in _request("GET", f"{api}/astronauts"):
        for dev in _request("GET", f"{api}/astronauts/{astro['id']}/devices"):
            if dev["id"] == device_id:
                return astro["id"], dev
    raise SystemExit(f"Device {device_id} not found. Run `python -m scripts.generate_data` to list devices.")


def latest_heart_rate(api: str, astronaut_id: int) -> float:
    rows = _request("GET", f"{api}/astronauts/{astronaut_id}/measurements?indicator={INDICATOR}")
    return float(rows[-1]["value"]) if rows else DEFAULT_BASE


def main() -> None:
    p = argparse.ArgumentParser(description="SIMULATED heart rate device for Houston Pulse.")
    p.add_argument("--device-id", type=int, required=True)
    p.add_argument("--token", required=True, help="device token printed by scripts.generate_data")
    p.add_argument("--interval", type=float, default=5.0, help="seconds between readings (default 5)")
    p.add_argument("--api", default="http://localhost:8000", help="API base URL")
    p.add_argument("--spike", action="store_true",
                   help=f"ramp up to ~{SPIKE_TARGET:.0f} bpm over ~30 s: crosses the AHA normal resting range "
                        "(100 bpm) and shows a live Watch alert (try it on Tanaka's shirt, device 6)")
    args = p.parse_args()
    api = args.api.rstrip("/")

    try:
        astronaut_id, dev = find_device(api, args.device_id)
    except urllib.error.URLError as e:
        raise SystemExit(f"Cannot reach the API at {api} ({e.reason}). Is the backend running?")
    if INDICATOR not in dev["indicators"]:
        raise SystemExit(f"{dev['name']} cannot send {INDICATOR} (supports: {', '.join(dev['indicators'])}).")

    base = latest_heart_rate(api, astronaut_id)
    print(f"SIMULATED device: {dev['name']} (id {args.device_id}), astronaut {astronaut_id}, "
          f"base {base:.0f} bpm, every {args.interval:g} s{', SPIKE' if args.spike else ''}. Ctrl+C to stop.")

    start = time.monotonic()
    try:
        while True:
            tick = time.monotonic()
            target = base
            if args.spike:
                progress = min(1.0, (time.monotonic() - start) / SPIKE_SECONDS)
                target = base + (SPIKE_TARGET - base) * progress
            value = round(target + random.gauss(0, NOISE_BPM))  # whole bpm, like the entry step
            value = max(20, min(250, value))  # stay inside the plausibility limits
            try:
                res = _request("POST", f"{api}/devices/{args.device_id}/readings",
                               {"readings": [{"indicator": INDICATOR, "value": value}]}, token=args.token)
                print(f"{time.strftime('%H:%M:%S')}  sent {value} bpm  (stored {res['stored']})")
            except urllib.error.HTTPError as e:
                print(f"{time.strftime('%H:%M:%S')}  rejected: HTTP {e.code} {_error_detail(e)}", file=sys.stderr)
                if e.code in (401, 404):
                    raise SystemExit(1)
            except urllib.error.URLError as e:
                print(f"{time.strftime('%H:%M:%S')}  API unreachable ({e.reason}), retrying…", file=sys.stderr)
            # Keep a steady rhythm: subtract the time the request took.
            time.sleep(max(0.0, args.interval - (time.monotonic() - tick)))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
