from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import date, datetime, time
from queue import Empty, Queue
from threading import Thread
from typing import cast

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from tactix.config import get_settings
from tactix.pipeline import (
    get_dashboard_payload,
    run_daily_game_sync,
    run_migrations,
    run_refresh_metrics,
)
from tactix.duckdb_store import (
    fetch_practice_queue,
    get_connection,
    grade_practice_attempt,
    init_schema,
)


def _extract_api_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    api_key = request.headers.get("x-api-key")
    if api_key:
        return api_key.strip()
    return None


def require_api_token(request: Request) -> None:
    if request.url.path == "/api/health":
        return
    settings = get_settings()
    expected = settings.api_token
    supplied = _extract_api_token(request)
    if not supplied or supplied != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )


app = FastAPI(
    title="TACTIX",
    version="0.1.0",
    dependencies=[Depends(require_api_token)],
    middleware=[
        Middleware(
            cast("type[object]", CORSMiddleware),
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ],
)


class PracticeAttemptRequest(BaseModel):
    tactic_id: int
    position_id: int
    attempted_uci: str
    source: str | None = None


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/jobs/daily_game_sync")
def trigger_daily_sync(
    source: str | None = Query(None),
    backfill_start_ms: int | None = Query(None, ge=0),
    backfill_end_ms: int | None = Query(None, ge=0),
) -> dict[str, object]:
    result = run_daily_game_sync(
        get_settings(source=source),
        source=source,
        window_start_ms=backfill_start_ms,
        window_end_ms=backfill_end_ms,
    )
    return {"status": "ok", "result": result}


@app.post("/api/jobs/refresh_metrics")
def trigger_refresh_metrics(source: str | None = Query(None)) -> dict[str, object]:
    result = run_refresh_metrics(get_settings(source=source), source=source)
    return {"status": "ok", "result": result}


@app.post("/api/jobs/migrations")
def trigger_migrations(source: str | None = Query(None)) -> dict[str, object]:
    result = run_migrations(get_settings(source=source), source=source)
    return {"status": "ok", "result": result}


@app.get("/api/dashboard")
def dashboard(
    source: str | None = Query(None),
    motif: str | None = Query(None),
    rating_bucket: str | None = Query(None),
    time_control: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
) -> dict[str, object]:
    start_datetime = _coerce_date_to_datetime(start_date)
    end_datetime = _coerce_date_to_datetime(end_date, end_of_day=True)
    return get_dashboard_payload(
        get_settings(source=source),
        source=source,
        motif=motif,
        rating_bucket=rating_bucket,
        time_control=time_control,
        start_date=start_datetime,
        end_date=end_datetime,
    )


@app.get("/api/practice/queue")
def practice_queue(
    source: str | None = Query(None),
    include_failed_attempt: bool = Query(False),
    limit: int = Query(20, ge=1, le=200),
) -> dict[str, object]:
    settings = get_settings(source=source)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    queue = fetch_practice_queue(
        conn,
        limit=limit,
        source=source or settings.source,
        include_failed_attempt=include_failed_attempt,
    )
    return {
        "source": source or settings.source,
        "include_failed_attempt": include_failed_attempt,
        "items": queue,
    }


@app.get("/api/practice/next")
def practice_next(
    source: str | None = Query(None),
    include_failed_attempt: bool = Query(False),
) -> dict[str, object]:
    settings = get_settings(source=source)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    items = fetch_practice_queue(
        conn,
        limit=1,
        source=source or settings.source,
        include_failed_attempt=include_failed_attempt,
        exclude_seen=True,
    )
    return {
        "source": source or settings.source,
        "include_failed_attempt": include_failed_attempt,
        "item": items[0] if items else None,
    }


@app.post("/api/practice/attempt")
def practice_attempt(payload: PracticeAttemptRequest) -> dict[str, object]:
    settings = get_settings(source=payload.source)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    try:
        result = grade_practice_attempt(
            conn,
            tactic_id=payload.tactic_id,
            position_id=payload.position_id,
            attempted_uci=payload.attempted_uci,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


def _format_sse(event: str, payload: dict[str, object]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n".encode("utf-8")


def _coerce_date_to_datetime(
    value: date | None, *, end_of_day: bool = False
) -> datetime | None:
    if value is None:
        return None
    if end_of_day:
        return datetime.combine(value, time.max)
    return datetime.combine(value, time.min)


@app.get("/api/jobs/stream")
def stream_jobs(
    job: str = Query("daily_game_sync"),
    source: str | None = Query(None),
) -> StreamingResponse:
    settings = get_settings(source=source)
    queue: Queue[object] = Queue()
    sentinel = object()

    def progress(payload: dict[str, object]) -> None:
        payload["job"] = job
        queue.put(("progress", payload))

    def worker() -> None:
        try:
            if job == "daily_game_sync":
                result = run_daily_game_sync(settings, source=source, progress=progress)
            elif job == "refresh_metrics":
                result = run_refresh_metrics(settings, source=source, progress=progress)
            elif job == "migrations":
                result = run_migrations(settings, source=source, progress=progress)
            else:
                raise ValueError(f"Unsupported job: {job}")
            queue.put(
                (
                    "complete",
                    {
                        "job": job,
                        "step": "complete",
                        "message": "Job complete",
                        "result": result,
                    },
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            queue.put(
                (
                    "error",
                    {
                        "job": job,
                        "step": "error",
                        "message": str(exc),
                    },
                )
            )
        finally:
            queue.put(sentinel)

    Thread(target=worker, daemon=True).start()

    def event_stream() -> Iterator[bytes]:
        yield b"retry: 1000\n\n"
        while True:
            try:
                item = queue.get(timeout=1)
            except Empty:
                yield b": keep-alive\n\n"
                continue
            if item is sentinel:
                break
            event, payload = cast(tuple[str, dict[str, object]], item)
            yield _format_sse(event, payload)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
