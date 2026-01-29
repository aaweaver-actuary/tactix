from __future__ import annotations

import json
import time as time_module
from collections import OrderedDict
from collections.abc import Iterator
from datetime import date, datetime, time
from queue import Empty, Queue
from threading import Lock, Thread
from typing import cast

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from tactix.base_db_store import BaseDbStoreContext
from tactix.config import get_settings
from tactix.logging_utils import get_logger
from tactix.airflow_client import fetch_dag_run, trigger_dag_run
from tactix.pipeline import (
    get_dashboard_payload,
    run_daily_game_sync,
    run_migrations,
    run_refresh_metrics,
)
from tactix.duckdb_store import (
    fetch_practice_queue,
    fetch_game_detail,
    fetch_raw_pgns_summary,
    get_connection,
    grade_practice_attempt,
    init_schema,
)
from tactix.postgres_store import (
    PostgresStore,
    serialize_status,
)

logger = get_logger(__name__)

_DASHBOARD_CACHE_TTL_S = 300
_DASHBOARD_CACHE_MAX_ENTRIES = 32
_DASHBOARD_CACHE: "OrderedDict[tuple[object, ...], tuple[float, dict[str, object]]]" = (
    OrderedDict()
)
_DASHBOARD_CACHE_LOCK = Lock()


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
    served_at_ms: int | None = None


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/postgres/status")
def postgres_status(limit: int = Query(10, ge=1, le=50)) -> dict[str, object]:
    settings = get_settings()
    store = PostgresStore(BaseDbStoreContext(settings=settings, logger=logger))
    status = store.get_status()
    payload = serialize_status(status)
    payload["events"] = store.fetch_ops_events(limit=limit)
    return payload


@app.get("/api/postgres/analysis")
def postgres_analysis(limit: int = Query(10, ge=1, le=200)) -> dict[str, object]:
    settings = get_settings()
    store = PostgresStore(BaseDbStoreContext(settings=settings, logger=logger))
    tactics = store.fetch_analysis_tactics(limit=limit)
    return {"status": "ok", "tactics": tactics}


@app.get("/api/postgres/raw_pgns")
def postgres_raw_pgns() -> dict[str, object]:
    settings = get_settings()
    store = PostgresStore(BaseDbStoreContext(settings=settings, logger=logger))
    return store.fetch_raw_pgns_summary()


@app.post("/api/jobs/daily_game_sync")
def trigger_daily_sync(
    source: str | None = Query(None),
    backfill_start_ms: int | None = Query(None, ge=0),
    backfill_end_ms: int | None = Query(None, ge=0),
    profile: str | None = Query(None),
) -> dict[str, object]:
    result = run_daily_game_sync(
        get_settings(source=source, profile=profile),
        source=source,
        window_start_ms=backfill_start_ms,
        window_end_ms=backfill_end_ms,
        profile=profile,
    )
    _refresh_dashboard_cache_async(_sources_for_cache_refresh(source))
    return {"status": "ok", "result": result}


@app.post("/api/jobs/refresh_metrics")
def trigger_refresh_metrics(source: str | None = Query(None)) -> dict[str, object]:
    result = run_refresh_metrics(get_settings(source=source), source=source)
    _refresh_dashboard_cache_async(_sources_for_cache_refresh(source))
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
    normalized_source = _normalize_source(source)
    settings = get_settings(source=normalized_source)
    cache_key = _dashboard_cache_key(
        settings,
        normalized_source,
        motif,
        rating_bucket,
        time_control,
        start_datetime,
        end_datetime,
    )
    cached = _get_cached_dashboard_payload(cache_key)
    if cached is not None:
        return cached
    payload = get_dashboard_payload(
        settings,
        source=normalized_source,
        motif=motif,
        rating_bucket=rating_bucket,
        time_control=time_control,
        start_date=start_datetime,
        end_date=end_datetime,
    )
    _set_dashboard_cache(cache_key, payload)
    return payload


@app.get("/api/practice/queue")
def practice_queue(
    source: str | None = Query(None),
    include_failed_attempt: bool = Query(False),
    limit: int = Query(20, ge=1, le=200),
) -> dict[str, object]:
    normalized_source = _normalize_source(source)
    settings = get_settings(source=normalized_source)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    queue = fetch_practice_queue(
        conn,
        limit=limit,
        source=normalized_source or settings.source,
        include_failed_attempt=include_failed_attempt,
    )
    return {
        "source": normalized_source or settings.source,
        "include_failed_attempt": include_failed_attempt,
        "items": queue,
    }


@app.get("/api/practice/next")
def practice_next(
    source: str | None = Query(None),
    include_failed_attempt: bool = Query(False),
) -> dict[str, object]:
    normalized_source = _normalize_source(source)
    settings = get_settings(source=normalized_source)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    items = fetch_practice_queue(
        conn,
        limit=1,
        source=normalized_source or settings.source,
        include_failed_attempt=include_failed_attempt,
        exclude_seen=True,
    )
    return {
        "source": normalized_source or settings.source,
        "include_failed_attempt": include_failed_attempt,
        "item": items[0] if items else None,
    }


@app.get("/api/raw_pgns/summary")
def raw_pgns_summary(source: str | None = Query(None)) -> dict[str, object]:
    normalized_source = _normalize_source(source)
    settings = get_settings(source=normalized_source)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    active_source = normalized_source or settings.source
    return {
        "source": active_source,
        "summary": fetch_raw_pgns_summary(conn, source=active_source),
    }


@app.get("/api/games/{game_id}")
def game_detail(
    game_id: str,
    source: str | None = Query(None),
) -> dict[str, object]:
    normalized_source = _normalize_source(source)
    settings = get_settings(source=normalized_source)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    payload = fetch_game_detail(
        conn,
        game_id=game_id,
        user=settings.user,
        source=normalized_source,
    )
    if not payload.get("pgn"):
        raise HTTPException(status_code=404, detail="Game not found")
    return payload


@app.post("/api/practice/attempt")
def practice_attempt(payload: PracticeAttemptRequest) -> dict[str, object]:
    settings = get_settings(source=payload.source)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    latency_ms: int | None = None
    if payload.served_at_ms is not None:
        now_ms = int(time_module.time() * 1000)
        latency_ms = max(0, now_ms - payload.served_at_ms)
    try:
        result = grade_practice_attempt(
            conn,
            tactic_id=payload.tactic_id,
            position_id=payload.position_id,
            attempted_uci=payload.attempted_uci,
            latency_ms=latency_ms,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


def _format_sse(event: str, payload: dict[str, object]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n".encode("utf-8")


def _airflow_enabled(settings) -> bool:
    return settings.airflow_enabled and bool(settings.airflow_base_url)


def _airflow_conf(
    source: str | None,
    profile: str | None,
    backfill_start_ms: int | None = None,
    backfill_end_ms: int | None = None,
    triggered_at_ms: int | None = None,
) -> dict[str, object]:
    conf: dict[str, object] = {}
    if source:
        conf["source"] = source
    if profile:
        key = "chesscom_profile" if source == "chesscom" else "lichess_profile"
        conf[key] = profile
    if backfill_start_ms is not None:
        conf["backfill_start_ms"] = backfill_start_ms
    if backfill_end_ms is not None:
        conf["backfill_end_ms"] = backfill_end_ms
    if triggered_at_ms is not None:
        conf["triggered_at_ms"] = triggered_at_ms
    return conf


def _airflow_run_id(payload: dict[str, object]) -> str:
    run_id = payload.get("dag_run_id") or payload.get("run_id")
    if not run_id:
        raise ValueError("Airflow response missing dag_run_id")
    return str(run_id)


def _trigger_airflow_daily_sync(
    settings,
    source: str | None,
    profile: str | None,
    backfill_start_ms: int | None = None,
    backfill_end_ms: int | None = None,
    triggered_at_ms: int | None = None,
) -> str:
    payload = trigger_dag_run(
        settings,
        "daily_game_sync",
        _airflow_conf(
            source,
            profile,
            backfill_start_ms=backfill_start_ms,
            backfill_end_ms=backfill_end_ms,
            triggered_at_ms=triggered_at_ms,
        ),
    )
    return _airflow_run_id(payload)


def _airflow_state(settings, run_id: str) -> str:
    payload = fetch_dag_run(settings, "daily_game_sync", run_id)
    return str(payload.get("state") or "unknown")


def _queue_progress(
    queue: Queue[object],
    job: str,
    step: str,
    message: str | None = None,
    extra: dict[str, object] | None = None,
) -> None:
    payload: dict[str, object] = {
        "job": job,
        "step": step,
        "timestamp": int(time_module.time()),
    }
    if message:
        payload["message"] = message
    if extra:
        payload.update(extra)
    queue.put(("progress", payload))


def _wait_for_airflow_run(
    settings,
    queue: Queue[object],
    job: str,
    run_id: str,
) -> str:
    start = time_module.time()
    last_state: str | None = None
    while True:
        state = _airflow_state(settings, run_id)
        if state != last_state:
            _queue_progress(
                queue,
                job,
                "airflow_state",
                message=state,
                extra={"state": state, "run_id": run_id},
            )
            last_state = state
        if state in {"success", "failed"}:
            return state
        if time_module.time() - start > settings.airflow_poll_timeout_s:
            raise TimeoutError("Airflow run timed out")
        time_module.sleep(settings.airflow_poll_interval_s)


def _coerce_date_to_datetime(
    value: date | None, *, end_of_day: bool = False
) -> datetime | None:
    if value is None:
        return None
    if end_of_day:
        return datetime.combine(value, time.max)
    return datetime.combine(value, time.min)


def _normalize_source(source: str | None) -> str | None:
    if source is None:
        return None
    trimmed = source.strip().lower()
    return None if trimmed == "all" else trimmed


def _dashboard_cache_key(
    settings,
    source: str | None,
    motif: str | None,
    rating_bucket: str | None,
    time_control: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> tuple[object, ...]:
    return (
        settings.user,
        str(settings.duckdb_path),
        source or "all",
        motif or "all",
        rating_bucket or "all",
        time_control or "all",
        start_date.isoformat() if start_date else None,
        end_date.isoformat() if end_date else None,
    )


def _get_cached_dashboard_payload(key: tuple[object, ...]) -> dict[str, object] | None:
    now = time_module.time()
    with _DASHBOARD_CACHE_LOCK:
        cached = _DASHBOARD_CACHE.get(key)
        if not cached:
            return None
        cached_at, payload = cached
        if now - cached_at > _DASHBOARD_CACHE_TTL_S:
            _DASHBOARD_CACHE.pop(key, None)
            return None
        _DASHBOARD_CACHE.move_to_end(key)
        return payload


def _set_dashboard_cache(key: tuple[object, ...], payload: dict[str, object]) -> None:
    with _DASHBOARD_CACHE_LOCK:
        _DASHBOARD_CACHE[key] = (time_module.time(), payload)
        _DASHBOARD_CACHE.move_to_end(key)
        while len(_DASHBOARD_CACHE) > _DASHBOARD_CACHE_MAX_ENTRIES:
            _DASHBOARD_CACHE.popitem(last=False)


def _clear_dashboard_cache() -> None:
    with _DASHBOARD_CACHE_LOCK:
        _DASHBOARD_CACHE.clear()


def _prime_dashboard_cache(
    source: str | None = None,
    motif: str | None = None,
    rating_bucket: str | None = None,
    time_control: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> None:
    settings = get_settings(source=source)
    payload = get_dashboard_payload(
        settings,
        source=source,
        motif=motif,
        rating_bucket=rating_bucket,
        time_control=time_control,
        start_date=start_date,
        end_date=end_date,
    )
    key = _dashboard_cache_key(
        settings,
        source,
        motif,
        rating_bucket,
        time_control,
        start_date,
        end_date,
    )
    _set_dashboard_cache(key, payload)


def _refresh_dashboard_cache_async(sources: list[str | None]) -> None:
    def worker() -> None:
        for source in sources:
            try:
                _prime_dashboard_cache(source=source)
            except Exception:  # pragma: no cover - defensive
                logger.exception(
                    "Failed to prime dashboard cache", extra={"source": source}
                )

    Thread(target=worker, daemon=True).start()


@app.on_event("startup")
def _warm_dashboard_cache_on_startup() -> None:
    _refresh_dashboard_cache_async([None, "lichess", "chesscom"])


def _sources_for_cache_refresh(source: str | None) -> list[str | None]:
    normalized = _normalize_source(source)
    sources: list[str | None] = [None]
    if normalized is not None:
        sources.append(normalized)
    return sources


@app.get("/api/jobs/stream")
def stream_jobs(
    job: str = Query("daily_game_sync"),
    source: str | None = Query(None),
    profile: str | None = Query(None),
    backfill_start_ms: int | None = Query(None, ge=0),
    backfill_end_ms: int | None = Query(None, ge=0),
) -> StreamingResponse:
    settings = get_settings(source=source, profile=profile)
    queue: Queue[object] = Queue()
    sentinel = object()
    triggered_at_ms = int(time_module.time() * 1000)
    effective_end_ms = backfill_end_ms
    if backfill_start_ms is not None or backfill_end_ms is not None:
        if effective_end_ms is None or effective_end_ms > triggered_at_ms:
            effective_end_ms = triggered_at_ms
        if (
            backfill_start_ms is not None
            and effective_end_ms is not None
            and backfill_start_ms >= effective_end_ms
        ):
            raise HTTPException(
                status_code=400,
                detail="Backfill window must end after start",
            )

    def progress(payload: dict[str, object]) -> None:
        payload["job"] = job
        queue.put(("progress", payload))

    def worker() -> None:
        try:
            if job == "daily_game_sync" and _airflow_enabled(settings):
                if backfill_start_ms is not None or effective_end_ms is not None:
                    _queue_progress(
                        queue,
                        job,
                        "backfill_window",
                        message="Backfill window resolved",
                        extra={
                            "backfill_start_ms": backfill_start_ms,
                            "backfill_end_ms": effective_end_ms,
                            "triggered_at_ms": triggered_at_ms,
                        },
                    )
                run_id = _trigger_airflow_daily_sync(
                    settings,
                    source,
                    profile,
                    backfill_start_ms=backfill_start_ms,
                    backfill_end_ms=effective_end_ms,
                    triggered_at_ms=triggered_at_ms,
                )
                _queue_progress(
                    queue,
                    job,
                    "airflow_triggered",
                    message="Airflow DAG triggered",
                    extra={"run_id": run_id},
                )
                state = _wait_for_airflow_run(settings, queue, job, run_id)
                if state != "success":
                    raise RuntimeError(f"Airflow run failed with state={state}")
                payload = get_dashboard_payload(
                    get_settings(source=source),
                    source=source,
                )
                logger.info(
                    "Airflow daily_game_sync completed; metrics_version=%s",
                    payload.get("metrics_version"),
                )
                result = {
                    "airflow_run_id": run_id,
                    "state": state,
                    "metrics_version": payload.get("metrics_version"),
                }
            elif job == "daily_game_sync":
                result = run_daily_game_sync(
                    settings,
                    source=source,
                    progress=progress,
                    profile=profile,
                    window_start_ms=backfill_start_ms,
                    window_end_ms=effective_end_ms,
                )
            elif job == "refresh_metrics":
                result = run_refresh_metrics(settings, source=source, progress=progress)
            elif job == "migrations":
                result = run_migrations(settings, source=source, progress=progress)
            else:
                raise ValueError(f"Unsupported job: {job}")
            if job in {"daily_game_sync", "refresh_metrics"}:
                _refresh_dashboard_cache_async(_sources_for_cache_refresh(source))
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
