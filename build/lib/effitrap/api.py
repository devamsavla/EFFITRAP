"""Optional HTTP API (pip install "effitrap[api]"; run: uvicorn effitrap.api:app).

POST /schedule   {"intensities": [...], "energy": 4, "cap": 1}
POST /route      {"budget_wh": 10, "requests": [[{"name":..,"wh":..,"quality":..}, ...], ...]}
GET  /day        ?texts=15&images=10&videos=3
GET  /health
"""
from __future__ import annotations

from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import __version__
from .router import Model, route_budgeted
from .schedule import flexible_start, linear_schedule, run_now, schedule_cost
from .units import day_of_ai

app = FastAPI(title="effitrap", version=__version__, description="Escape AI's efficiency trap ⚡")


class ScheduleIn(BaseModel):
    intensities: List[float] = Field(..., min_length=1)
    energy: float = Field(..., ge=0)
    cap: float = Field(..., gt=0)


class ModelIn(BaseModel):
    name: str
    wh: float = Field(..., ge=0)
    quality: float


class RouteIn(BaseModel):
    budget_wh: float = Field(..., gt=0)
    requests: List[List[ModelIn]] = Field(..., min_length=1)
    resolution_wh: float = 0.1


@app.get("/health")
def health():
    return {"ok": True, "version": __version__, "mood": "⚡ efficient"}


@app.post("/schedule")
def schedule(body: ScheduleIn):
    c = body.intensities
    try:
        plans = {
            "run_now": run_now(c, body.energy, body.cap),
            "flexible_start": flexible_start(c, body.energy, body.cap),
            "optimal": linear_schedule(c, body.energy, body.cap),
        }
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {k: {"x": v, "emissions": schedule_cost(c, v)} for k, v in plans.items()}


@app.post("/route")
def route(body: RouteIn):
    opts = [[Model(m.name, m.wh, m.quality) for m in r] for r in body.requests]
    try:
        q, chosen = route_budgeted(opts, body.budget_wh, body.resolution_wh)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"total_quality": q, "energy_wh": sum(m.wh for m in chosen), "chosen": [m.name for m in chosen]}


@app.get("/day")
def day(texts: int = 15, images: int = 10, videos: int = 3):
    return day_of_ai(texts, images, videos)
