"""Carbon-intensity inputs.

SAMPLE_DAY  an illustrative 24-hour curve (g CO2/kWh) shaped like MIT Technology Review's
            California example: under 70 in the afternoon, ~300 at night. NOT real data.
load_csv    your own data: one intensity per line, or a CSV with an 'intensity' column.
fetch_gb_forecast
            optional live half-hourly forecast for Great Britain from the National Grid ESO
            Carbon Intensity API (api.carbonintensity.org.uk, no key needed). Standard library
            only. Not exercised in the offline test suite.
"""
from __future__ import annotations

import csv
import json
import urllib.request
from datetime import datetime, timezone
from typing import List

SAMPLE_DAY = [300, 300, 295, 290, 285, 270, 240, 200, 160, 120, 90, 75,
              68, 65, 66, 70, 90, 130, 190, 250, 280, 295, 300, 300]


def load_csv(path: str) -> List[float]:
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return []
    header = [h.strip().lower() for h in rows[0]]
    if "intensity" in header:
        i = header.index("intensity")
        return [float(r[i]) for r in rows[1:] if r]
    return [float(r[0]) for r in rows if r]


def parse_gb(payload: dict) -> List[float]:
    """Forecast values from a GB Carbon Intensity API response (/intensity/{from}/fw48h)."""
    return [float(d["intensity"]["forecast"]) for d in payload["data"]
            if d.get("intensity", {}).get("forecast") is not None]


def parse_electricitymaps(payload: dict) -> List[float]:
    """Forecast values from an Electricity Maps /v3/carbon-intensity/forecast response."""
    return [float(d["carbonIntensity"]) for d in payload["forecast"] if d.get("carbonIntensity") is not None]


def _get_json(url: str, headers: dict, timeout: float, retries: int = 2) -> dict:
    last = None
    for _ in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", **headers})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except Exception as e:          # network errors, timeouts, bad JSON
            last = e
    raise ConnectionError(f"could not fetch forecast: {last}")


def fetch_gb_forecast(hours: int = 24, timeout: float = 10.0) -> List[float]:
    """Half-hourly forecast for the next `hours` hours, Great Britain (free, no key).
    Checked against the live API on 2026-11-24 (97 half-hour values)."""
    start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    payload = _get_json(f"https://api.carbonintensity.org.uk/intensity/{start}/fw48h", {}, timeout)
    return parse_gb(payload)[: int(hours * 2)]


def fetch_electricitymaps_forecast(zone: str, token: str, hours: int = 24, timeout: float = 10.0) -> List[float]:
    """Hourly forecast for any Electricity Maps zone (e.g. "DE", "IN-WE", "US-CAL-CISO").
    Needs an API token with forecast access (not part of their free tier)."""
    url = f"https://api.electricitymap.org/v3/carbon-intensity/forecast?zone={zone}"
    return parse_electricitymaps(_get_json(url, {"auth-token": token}, timeout))[: int(hours)]
