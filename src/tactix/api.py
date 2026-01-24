from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tactix.config import get_settings
from tactix.pipeline import get_dashboard_payload, run_daily_game_sync

settings = get_settings()

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
def trigger_daily_sync() -> dict[str, object]:
    result = run_daily_game_sync(settings)
    return {"status": "ok", "result": result}


@app.get("/api/dashboard")
def dashboard() -> dict[str, object]:
    return get_dashboard_payload(settings)
