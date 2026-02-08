"""Use cases for dashboard-related API endpoints."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from tactix._resolve_dashboard_filters import _resolve_dashboard_filters
from tactix.build_dashboard_cache_key__api_cache import _dashboard_cache_key
from tactix.config import Settings, get_settings
from tactix.dashboard_query import DashboardQuery
from tactix.dashboard_query_filters import DashboardQueryFilters
from tactix.db.dashboard_repository_provider import (
    fetch_motif_stats,
    fetch_pipeline_table_counts,
    fetch_trend_stats,
)
from tactix.db.duckdb_store import fetch_version, init_schema
from tactix.db.duckdb_unit_of_work import DuckDbUnitOfWork
from tactix.db.raw_pgn_repository_provider import fetch_raw_pgns_summary
from tactix.get_cached_dashboard_payload__api_cache import _get_cached_dashboard_payload
from tactix.normalize_source__source import _normalize_source
from tactix.pipeline import get_dashboard_payload
from tactix.ports.unit_of_work import UnitOfWork
from tactix.set_dashboard_cache__api_cache import _set_dashboard_cache

ResultT = TypeVar("ResultT")


@dataclass
class DashboardUseCase:  # pylint: disable=too-many-instance-attributes
    resolve_dashboard_filters: Callable[
        [DashboardQueryFilters],
        tuple[Any, Any, str | None, Settings],
    ] = _resolve_dashboard_filters
    dashboard_cache_key: Callable[
        [Settings, DashboardQuery],
        tuple[object, ...],
    ] = _dashboard_cache_key
    get_cached_dashboard_payload: Callable[[tuple[object, ...]], dict[str, object] | None] = (
        _get_cached_dashboard_payload
    )
    set_dashboard_cache: Callable[
        [tuple[object, ...], dict[str, object]],
        None,
    ] = _set_dashboard_cache
    get_dashboard_payload: Callable[[DashboardQuery, Settings], dict[str, object]] = (
        get_dashboard_payload
    )
    fetch_pipeline_table_counts: Callable[[Any, DashboardQuery], dict[str, int]] = (
        fetch_pipeline_table_counts
    )
    fetch_motif_stats: Callable[..., object] = fetch_motif_stats
    fetch_trend_stats: Callable[..., object] = fetch_trend_stats
    fetch_raw_pgns_summary: Callable[..., object] = fetch_raw_pgns_summary
    fetch_version: Callable[[Any], int] = fetch_version
    unit_of_work_factory: Callable[[Path], UnitOfWork] = DuckDbUnitOfWork
    init_schema: Callable[[Any], None] = init_schema
    get_settings: Callable[..., Settings] = get_settings
    normalize_source: Callable[[str | None], str | None] = _normalize_source

    def get_dashboard(
        self,
        filters: DashboardQueryFilters,
        motif: str | None,
    ) -> dict[str, object]:
        start_datetime, end_datetime, normalized_source, settings = self.resolve_dashboard_filters(
            filters
        )
        query = DashboardQuery(
            source=normalized_source,
            motif=motif,
            rating_bucket=filters.rating_bucket,
            time_control=filters.time_control,
            start_date=start_datetime,
            end_date=end_datetime,
        )
        cache_key = self.dashboard_cache_key(settings, query)
        cached = self.get_cached_dashboard_payload(cache_key)
        if cached is not None:
            return cached
        payload = self.get_dashboard_payload(query, settings)
        self.set_dashboard_cache(cache_key, payload)
        return payload

    def get_summary(
        self,
        filters: DashboardQueryFilters,
        db_name: str | None,
    ) -> dict[str, object]:
        start_datetime, end_datetime, normalized_source, settings = self.resolve_dashboard_filters(
            filters
        )
        settings = self._apply_db_name(settings, db_name)
        query = DashboardQuery(
            source=normalized_source,
            rating_bucket=filters.rating_bucket,
            time_control=filters.time_control,
            start_date=start_datetime,
            end_date=end_datetime,
        )
        summary = self._run_with_uow(
            settings,
            lambda conn: self.fetch_pipeline_table_counts(conn, query),
        )
        response_source = "all" if normalized_source is None else normalized_source
        return {"source": response_source, "summary": summary}

    def get_motif_stats(self, filters: DashboardQueryFilters) -> dict[str, object]:
        return self._build_stats_payload(filters, self.fetch_motif_stats, "motifs")

    def get_trend_stats(self, filters: DashboardQueryFilters) -> dict[str, object]:
        return self._build_stats_payload(filters, self.fetch_trend_stats, "trends")

    def get_raw_pgns_summary(self, source: str | None) -> dict[str, object]:
        normalized_source = self.normalize_source(source)
        settings = self.get_settings(source=normalized_source)
        active_source = normalized_source or settings.source
        return self._run_with_uow(
            settings,
            lambda conn: {
                "source": active_source,
                "summary": self.fetch_raw_pgns_summary(conn, source=active_source),
            },
        )

    def _build_stats_payload(
        self,
        filters: DashboardQueryFilters,
        stats_fetcher: Callable[..., object],
        stats_key: str,
    ) -> dict[str, object]:
        start_datetime, end_datetime, normalized_source, settings = self.resolve_dashboard_filters(
            filters
        )
        response_source = "all" if normalized_source is None else normalized_source

        def handler(conn):
            return {
                "source": response_source,
                "metrics_version": self.fetch_version(conn),
                stats_key: stats_fetcher(
                    conn,
                    source=normalized_source,
                    rating_bucket=filters.rating_bucket,
                    time_control=filters.time_control,
                    start_date=start_datetime,
                    end_date=end_datetime,
                ),
            }

        return self._run_with_uow(settings, handler)

    def _apply_db_name(self, settings: Settings, db_name: str | None) -> Settings:
        if not db_name:
            return settings
        safe_name = Path(db_name).name
        filename = safe_name if safe_name.endswith(".duckdb") else f"{safe_name}.duckdb"
        settings.duckdb_path = settings.data_dir / filename
        return settings

    def _run_with_uow(
        self,
        settings: Settings,
        handler: Callable[[Any], ResultT],
    ) -> ResultT:
        uow = self.unit_of_work_factory(settings.duckdb_path)
        conn = uow.begin()
        try:
            self.init_schema(conn)
            result = handler(conn)
        except Exception:
            uow.rollback()
            raise
        else:
            uow.commit()
        finally:
            uow.close()
        return result


def get_dashboard_use_case() -> DashboardUseCase:
    return DashboardUseCase()


__all__ = ["DashboardUseCase", "get_dashboard_use_case"]
