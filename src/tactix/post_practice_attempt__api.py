"""API handler for practice attempt submissions."""

from __future__ import annotations

import time as time_module

from fastapi import HTTPException

from tactix.config import get_settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.tactic_repository_provider import tactic_repository
from tactix.models import PracticeAttemptRequest


def practice_attempt(payload: PracticeAttemptRequest) -> dict[str, object]:
    """Grade a practice attempt and return the result."""
    settings = get_settings(source=payload.source)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    latency_ms: int | None = None
    if payload.served_at_ms is not None:
        now_ms = int(time_module.time() * 1000)
        latency_ms = max(0, now_ms - payload.served_at_ms)
    try:
        repo = tactic_repository(conn)
        result = repo.grade_practice_attempt(
            payload.tactic_id,
            payload.position_id,
            payload.attempted_uci,
            latency_ms=latency_ms,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result
