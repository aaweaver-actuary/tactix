"""API endpoint to run the pipeline with explicit date ranges."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException

from tactix.coerce_date_to_datetime__datetime import _coerce_date_to_datetime
from tactix.config import get_settings
from tactix.dashboard_query import DashboardQuery
from tactix.db.dashboard_repository_provider import (
    fetch_opportunity_motif_counts,
    fetch_pipeline_table_counts,
)
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.list_sources_for_cache_refresh__api_cache import _sources_for_cache_refresh
from tactix.normalize_source__source import _normalize_source
from tactix.pipeline import run_daily_game_sync
from tactix.pipeline_run_filters import PipelineRunFilters
from tactix.refresh_dashboard_cache_async__api_cache import _refresh_dashboard_cache_async


def run_pipeline(  # pragma: no cover
    filters: Annotated[PipelineRunFilters, Depends()],
) -> dict[str, object]:
    """Run the pipeline for the provided date range and return counts."""
    normalized_source = _normalize_source(filters.source)
    settings = _resolve_pipeline_settings(
        normalized_source,
        filters,
    )
    start_datetime, end_datetime, window_start_ms, window_end_ms = _resolve_window_range(filters)
    result = run_daily_game_sync(
        settings,
        source=normalized_source,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
        profile=None,
    )
    _refresh_dashboard_cache_async(_sources_for_cache_refresh(normalized_source))
    counts, motif_counts = _fetch_pipeline_counts(
        settings.duckdb_path,
        DashboardQuery(
            source=normalized_source,
            start_date=start_datetime,
            end_date=end_datetime,
        ),
    )
    return {
        "status": "ok",
        "result": result,
        "counts": counts,
        "motif_counts": motif_counts,
        "window_start_ms": window_start_ms,
        "window_end_ms": window_end_ms,
    }


def _fetch_pipeline_counts(  # pragma: no cover
    db_path: Path,
    query: DashboardQuery,
) -> tuple[dict[str, int], dict[str, int]]:
    conn = get_connection(db_path)
    try:
        init_schema(conn)
        return (
            fetch_pipeline_table_counts(conn, query),
            fetch_opportunity_motif_counts(conn, query),
        )
    finally:
        conn.close()


def _resolve_pipeline_settings(  # pragma: no cover
    normalized_source: str | None,
    filters: PipelineRunFilters,
):
    settings = get_settings(source=normalized_source, profile=filters.profile)
    _apply_user_settings(settings, filters.user_id)
    _apply_fixture_settings(settings, filters.use_fixture, filters.fixture_name)
    _apply_db_settings(settings, filters.db_name, filters.reset_db)
    return settings


def _apply_user_settings(settings, user_id: str | None) -> None:  # pragma: no cover
    if not user_id:
        return
    settings.user = user_id
    settings.lichess.user = user_id
    settings.chesscom.user = user_id


def _apply_fixture_settings(  # pragma: no cover
    settings,
    use_fixture: bool,
    fixture_name: str | None,
) -> None:
    if not use_fixture:
        return
    settings.chesscom.token = None
    settings.chesscom_use_fixture_when_no_token = True
    settings.stockfish_movetime_ms = 60
    settings.stockfish_depth = 8
    settings.stockfish_multipv = 2
    if not fixture_name:
        return
    safe_name = Path(fixture_name).name
    repo_root = Path(__file__).resolve().parents[2]
    settings.chesscom_fixture_pgn_path = repo_root / "tests" / "fixtures" / safe_name


def _apply_db_settings(settings, db_name: str | None, reset_db: bool) -> None:  # pragma: no cover
    if not db_name:
        return
    safe_name = Path(db_name).name
    filename = safe_name if safe_name.endswith(".duckdb") else f"{safe_name}.duckdb"
    settings.duckdb_path = settings.data_dir / filename
    if reset_db and settings.duckdb_path.exists():
        settings.duckdb_path.unlink()


def _resolve_window_range(  # pragma: no cover
    filters: PipelineRunFilters,
) -> tuple[datetime | None, datetime | None, int | None, int | None]:
    start_datetime = _coerce_date_to_datetime(filters.start_date)
    end_datetime = _coerce_date_to_datetime(filters.end_date, end_of_day=True)
    window_start_ms = _datetime_to_ms(start_datetime)
    window_end_ms = _datetime_to_ms(end_datetime)
    if window_end_ms is not None:
        window_end_ms += 1
    if (
        window_start_ms is not None
        and window_end_ms is not None
        and window_start_ms >= window_end_ms
    ):
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    return start_datetime, end_datetime, window_start_ms, window_end_ms


def _datetime_to_ms(value: datetime | None) -> int | None:  # pragma: no cover
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return int(value.timestamp() * 1000)


__all__ = ["run_pipeline"]
