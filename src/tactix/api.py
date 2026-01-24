from __future__ import annotations

import json
from queue import Empty, Queue
from threading import Thread

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from tactix.config import get_settings
from tactix.pipeline import (
    get_dashboard_payload,
    run_daily_game_sync,
    run_refresh_metrics,
)
from tactix.duckdb_store import fetch_practice_queue, get_connection, init_schema

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
    )
    return {
        "source": source or settings.source,
        "include_failed_attempt": include_failed_attempt,
        "item": items[0] if items else None,
    }


def _format_sse(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


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

    def event_stream():
        yield "retry: 1000\n\n"
        while True:
            try:
                item = queue.get(timeout=1)
            except Empty:
                yield ": keep-alive\n\n"
                continue
            if item is sentinel:
                break
            event, payload = item
            yield _format_sse(event, payload)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
