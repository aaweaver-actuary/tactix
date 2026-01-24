from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from tactix.config import get_settings
from tactix.pipeline import (
    get_dashboard_payload,
    run_daily_game_sync,
    run_refresh_metrics,
)

app = FastAPI(title="TACTIX", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/jobs/daily_game_sync")
def trigger_daily_sync(source: str | None = Query(None)) -> dict[str, object]:
    result = run_daily_game_sync(get_settings(source=source), source=source)
    return {"status": "ok", "result": result}


@app.post("/api/jobs/refresh_metrics")
def trigger_refresh_metrics(source: str | None = Query(None)) -> dict[str, object]:
    result = run_refresh_metrics(get_settings(source=source), source=source)
    return {"status": "ok", "result": result}


@app.get("/api/dashboard")
def dashboard(source: str | None = Query(None)) -> dict[str, object]:
    return get_dashboard_payload(get_settings(source=source), source=source)
