"""Use case for pipeline run endpoints."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from tactix.coerce_date_to_datetime__datetime import _coerce_date_to_datetime
from tactix.config import Settings, get_settings
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
from tactix.trace_context import trace_context


class PipelineWindowError(ValueError):
    """Raised when a pipeline run window is invalid."""


@dataclass
class PipelineRunUseCase:  # pylint: disable=too-many-instance-attributes
    get_settings: Callable[..., Settings] = get_settings
    normalize_source: Callable[[str | None], str | None] = _normalize_source
    coerce_date_to_datetime: Callable[..., Any] = _coerce_date_to_datetime
    run_daily_game_sync: Callable[..., object] = run_daily_game_sync
    refresh_dashboard_cache_async: Callable[[list[str | None]], None] = (
        _refresh_dashboard_cache_async
    )
    sources_for_cache_refresh: Callable[[str | None], list[str | None]] = _sources_for_cache_refresh
    fetch_pipeline_table_counts: Callable[[Any, DashboardQuery], dict[str, int]] = (
        fetch_pipeline_table_counts
    )
    fetch_opportunity_motif_counts: Callable[[Any, DashboardQuery], dict[str, int]] = (
        fetch_opportunity_motif_counts
    )
    get_connection: Callable[[Path], Any] = get_connection
    init_schema: Callable[[Any], None] = init_schema

    def run(self, filters: PipelineRunFilters) -> dict[str, object]:
        normalized_source = self.normalize_source(filters.source)
        settings = self._resolve_pipeline_settings(normalized_source, filters)
        run_id = uuid4().hex
        settings.run_id = run_id
        start_datetime, end_datetime, window_start_ms, window_end_ms = self._resolve_window_range(
            filters
        )
        with trace_context(run_id=run_id, op_id="pipeline.run"):
            result = self.run_daily_game_sync(
                settings,
                source=normalized_source,
                window_start_ms=window_start_ms,
                window_end_ms=window_end_ms,
                profile=None,
            )
            self.refresh_dashboard_cache_async(self.sources_for_cache_refresh(normalized_source))
            counts, motif_counts = self._fetch_pipeline_counts(
                settings.duckdb_path,
                DashboardQuery(
                    source=normalized_source,
                    start_date=start_datetime,
                    end_date=end_datetime,
                ),
            )
        return {
            "status": "ok",
            "run_id": run_id,
            "result": result,
            "counts": counts,
            "motif_counts": motif_counts,
            "window_start_ms": window_start_ms,
            "window_end_ms": window_end_ms,
        }

    def _fetch_pipeline_counts(
        self,
        db_path: Path,
        query: DashboardQuery,
    ) -> tuple[dict[str, int], dict[str, int]]:
        conn = self.get_connection(db_path)
        try:
            self.init_schema(conn)
            return (
                self.fetch_pipeline_table_counts(conn, query),
                self.fetch_opportunity_motif_counts(conn, query),
            )
        finally:
            conn.close()

    def _resolve_pipeline_settings(
        self,
        normalized_source: str | None,
        filters: PipelineRunFilters,
    ) -> Settings:
        settings = self.get_settings(source=normalized_source, profile=filters.profile)
        self._apply_user_settings(settings, filters.user_id)
        self._apply_fixture_settings(settings, filters.use_fixture, filters.fixture_name)
        self._apply_db_settings(settings, filters.db_name, filters.reset_db)
        return settings

    def _apply_user_settings(self, settings: Settings, user_id: str | None) -> None:
        if not user_id:
            return
        settings.user = user_id
        settings.lichess.user = user_id
        settings.chesscom.user = user_id

    def _apply_fixture_settings(
        self,
        settings: Settings,
        use_fixture: bool,
        fixture_name: str | None,
    ) -> None:
        if not use_fixture and not fixture_name:
            return
        settings.chesscom.token = None
        settings.lichess.token = None
        settings.use_fixture_when_no_token = True
        settings.chesscom_use_fixture_when_no_token = True
        settings.stockfish_movetime_ms = 60
        settings.stockfish_depth = 8
        settings.stockfish_multipv = 2
        if not fixture_name:
            return
        safe_name = Path(fixture_name).name
        repo_root = Path(__file__).resolve().parents[4]
        settings.fixture_pgn_path = repo_root / "tests" / "fixtures" / safe_name
        settings.chesscom_fixture_pgn_path = repo_root / "tests" / "fixtures" / safe_name
        settings.lichess_token_cache_path = settings.lichess_token_cache_path.with_name(
            "lichess_token_fixture.json"
        )

    def _apply_db_settings(self, settings: Settings, db_name: str | None, reset_db: bool) -> None:
        if not db_name:
            return
        safe_name = Path(db_name).name
        filename = safe_name if safe_name.endswith(".duckdb") else f"{safe_name}.duckdb"
        settings.duckdb_path = settings.data_dir / filename
        if reset_db and settings.duckdb_path.exists():
            settings.duckdb_path.unlink()

    def _resolve_window_range(
        self,
        filters: PipelineRunFilters,
    ) -> tuple[datetime | None, datetime | None, int | None, int | None]:
        start_datetime = self.coerce_date_to_datetime(filters.start_date)
        end_datetime = self.coerce_date_to_datetime(filters.end_date, end_of_day=True)
        window_start_ms = self._datetime_to_ms(start_datetime)
        window_end_ms = self._datetime_to_ms(end_datetime)
        if window_end_ms is not None:
            window_end_ms += 1
        if (
            window_start_ms is not None
            and window_end_ms is not None
            and window_start_ms >= window_end_ms
        ):
            raise PipelineWindowError("start_date must be before end_date")
        return start_datetime, end_datetime, window_start_ms, window_end_ms

    def _datetime_to_ms(self, value: datetime | None) -> int | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return int(value.timestamp() * 1000)


def get_pipeline_run_use_case() -> PipelineRunUseCase:
    return PipelineRunUseCase()


__all__ = ["PipelineRunUseCase", "PipelineWindowError", "get_pipeline_run_use_case"]
