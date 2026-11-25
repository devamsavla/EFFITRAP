"""Watt-hours, translated for humans.

1 Wh  = a 1-watt device running for 1 hour (= 3,600 joules)
1 kWh = 1,000 Wh.  Each step up (Wh -> kWh -> MWh -> GWh -> TWh) is x1,000.

Reference points:
    phone charge   ~15 Wh   (IEA 2025)
    laptop charge  ~60 Wh   (IEA 2025)
    TV            ~96 W     (derived: Google says 0.24 Wh is about 9 seconds of TV)
Per-task energies (IEA 2025 lab tests, GPU only):
    short text 0.3 Wh, image 1.7 Wh, 6-second video 115 Wh
"""
from __future__ import annotations

from typing import Dict

PHONE_WH = 15.0
LAPTOP_WH = 60.0
TV_W = 0.24 / (9 / 3600)  # = 96 W, derived from Google's comparison

TASK_WH = {"text": 0.3, "image": 1.7, "video": 115.0}


def everyday(wh: float) -> Dict[str, float]:
    return {
        "wh": wh,
        "kwh": wh / 1000,
        "phone_charges": wh / PHONE_WH,
        "laptop_charges": wh / LAPTOP_WH,
        "tv_seconds": wh / TV_W * 3600,
    }


def day_of_ai(texts: int = 15, images: int = 10, videos: int = 3) -> Dict[str, float]:
    """MIT Technology Review's 'day of AI use' mix, priced with IEA per-task energies."""
    parts = {
        "text": texts * TASK_WH["text"],
        "image": images * TASK_WH["image"],
        "video": videos * TASK_WH["video"],
    }
    total = sum(parts.values())
    return {**{f"{k}_wh": v for k, v in parts.items()}, **everyday(total)}
