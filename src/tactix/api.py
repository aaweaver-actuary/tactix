from __future__ import annotations

from typing import cast

from fastapi import Depends, FastAPI
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from tactix.apply_airflow_optional_conf__airflow_jobs import _apply_airflow_optional_conf
from tactix.build_airflow_conf__airflow_jobs import _airflow_conf
from tactix.build_dashboard_cache_key__api_cache import _dashboard_cache_key
from tactix.check_airflow_enabled__airflow_settings import _airflow_enabled
from tactix.clear_dashboard_cache__api_cache import _clear_dashboard_cache
from tactix.coerce_backfill_end_ms__airflow_jobs import _coerce_backfill_end_ms
from tactix.coerce_cache_value__api_cache import _cache_value
from tactix.coerce_date_cache_value__api_cache import _date_cache_value
from tactix.coerce_date_to_datetime__datetime import _coerce_date_to_datetime
from tactix.dashboard_cache_state__api_cache import (
    _DASHBOARD_CACHE,
    _DASHBOARD_CACHE_MAX_ENTRIES,
    _DASHBOARD_CACHE_TTL_S,
)
from tactix.ensure_airflow_success__airflow_jobs import _ensure_airflow_success
from tactix.event_stream__job_stream import _event_stream
from tactix.extract_api_token__request_auth import _extract_api_token
from tactix.format_sse__api_streaming import _format_sse
from tactix.get_airflow_run_id__airflow_response import _airflow_run_id
from tactix.get_airflow_state__airflow_jobs import _airflow_state
from tactix.get_cached_dashboard_payload__api_cache import _get_cached_dashboard_payload
from tactix.get_dashboard__api import dashboard, motif_stats, trend_stats
from tactix.get_game_detail__api import game_detail
from tactix.get_health__api import health
from tactix.get_postgres_analysis__api import postgres_analysis
from tactix.get_postgres_raw_pgns__api import postgres_raw_pgns
from tactix.get_postgres_status__api import postgres_status
from tactix.get_practice_next__api import practice_next
from tactix.get_practice_queue__api import practice_queue
from tactix.get_raw_pgns_summary__api import raw_pgns_summary
from tactix.get_tactics_search__api import tactics_search
from tactix.list_sources_for_cache_refresh__api_cache import _sources_for_cache_refresh
from tactix.manage_lifespan__fastapi import lifespan
from tactix.models import PracticeAttemptRequest
from tactix.normalize_source__source import _normalize_source
from tactix.post_practice_attempt__api import practice_attempt
from tactix.prime_dashboard_cache__api_cache import _prime_dashboard_cache
from tactix.queue_backfill_window__job_stream import _queue_backfill_window
from tactix.queue_progress__job_stream import _queue_progress
from tactix.raise_unsupported_job__api_jobs import _raise_unsupported_job
from tactix.refresh_dashboard_cache_async__api_cache import _refresh_dashboard_cache_async
from tactix.require_api_token__request_auth import require_api_token
from tactix.resolve_backfill_end_ms__airflow_jobs import _resolve_backfill_end_ms
from tactix.run_airflow_daily_sync_job__job_stream import _run_airflow_daily_sync_job
from tactix.run_stream_job__job_stream import _run_stream_job
from tactix.set_dashboard_cache__api_cache import _set_dashboard_cache
from tactix.stream_job_worker__job_stream import _stream_job_worker
from tactix.stream_jobs__api import stream_jobs
from tactix.trigger_airflow_daily_sync__airflow_jobs import _trigger_airflow_daily_sync
from tactix.trigger_daily_sync__api_jobs import trigger_daily_sync
from tactix.trigger_migrations__api_jobs import trigger_migrations
from tactix.trigger_refresh_metrics__api_jobs import trigger_refresh_metrics
from tactix.validate_backfill_window__airflow_jobs import _validate_backfill_window
from tactix.wait_for_airflow_run__job_stream import _wait_for_airflow_run

app = FastAPI(
    title="TACTIX",
    version="0.1.0",
    dependencies=[Depends(require_api_token)],
    lifespan=lifespan,
    middleware=[
        Middleware(
            cast("type[object]", CORSMiddleware),
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ],
)

app.get("/api/health")(health)
app.get("/api/postgres/status")(postgres_status)
app.get("/api/postgres/analysis")(postgres_analysis)
app.get("/api/postgres/raw_pgns")(postgres_raw_pgns)
app.post("/api/jobs/daily_game_sync")(trigger_daily_sync)
app.post("/api/jobs/refresh_metrics")(trigger_refresh_metrics)
app.post("/api/jobs/migrations")(trigger_migrations)
app.get("/api/dashboard")(dashboard)
app.get("/api/practice/queue")(practice_queue)
app.get("/api/practice/next")(practice_next)
app.get("/api/raw_pgns/summary")(raw_pgns_summary)
app.get("/api/tactics/search")(tactics_search)
app.get("/api/games/{game_id}")(game_detail)
app.post("/api/practice/attempt")(practice_attempt)
app.get("/api/jobs/stream")(stream_jobs)
app.get("/api/stats/motifs")(motif_stats)
app.get("/api/stats/trends")(trend_stats)

__all__ = [
    "_DASHBOARD_CACHE",
    "_DASHBOARD_CACHE_MAX_ENTRIES",
    "_DASHBOARD_CACHE_TTL_S",
    "PracticeAttemptRequest",
    "_airflow_conf",
    "_airflow_enabled",
    "_airflow_run_id",
    "_airflow_state",
    "_apply_airflow_optional_conf",
    "_cache_value",
    "_clear_dashboard_cache",
    "_coerce_backfill_end_ms",
    "_coerce_date_to_datetime",
    "_dashboard_cache_key",
    "_date_cache_value",
    "_ensure_airflow_success",
    "_event_stream",
    "_extract_api_token",
    "_format_sse",
    "_get_cached_dashboard_payload",
    "_normalize_source",
    "_prime_dashboard_cache",
    "_queue_backfill_window",
    "_queue_progress",
    "_raise_unsupported_job",
    "_refresh_dashboard_cache_async",
    "_resolve_backfill_end_ms",
    "_run_airflow_daily_sync_job",
    "_run_stream_job",
    "_set_dashboard_cache",
    "_sources_for_cache_refresh",
    "_stream_job_worker",
    "_trigger_airflow_daily_sync",
    "_validate_backfill_window",
    "_wait_for_airflow_run",
    "app",
    "dashboard",
    "game_detail",
    "health",
    "lifespan",
    "motif_stats",
    "postgres_analysis",
    "postgres_raw_pgns",
    "postgres_status",
    "practice_attempt",
    "practice_next",
    "practice_queue",
    "raw_pgns_summary",
    "require_api_token",
    "stream_jobs",
    "tactics_search",
    "trend_stats",
    "trigger_daily_sync",
    "trigger_migrations",
    "trigger_refresh_metrics",
]
