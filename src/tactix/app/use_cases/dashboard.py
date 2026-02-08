"""Use cases for dashboard-related API endpoints."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from tactix.app.use_cases.dependencies import (
    DashboardCache,
    DashboardCacheKeyBuilder,
    DashboardFiltersResolver,
    DashboardPayloadFetcher,
    DashboardRepositoryFactory,
    DashboardStatsService,
    DashboardVersionProvider,
    RawPgnRepositoryFactory,
    SettingsProvider,
    SourceNormalizer,
    UnitOfWorkRunner,
)
from tactix.app.wiring import (
    DefaultDashboardCache,
    DefaultDashboardCacheKeyBuilder,
    DefaultDashboardFiltersResolver,
    DefaultDashboardPayloadFetcher,
    DefaultDashboardRepositoryFactory,
    DefaultDashboardStatsService,
    DefaultDashboardVersionProvider,
    DefaultRawPgnRepositoryFactory,
    DefaultSettingsProvider,
    DefaultSourceNormalizer,
    DuckDbUnitOfWorkRunner,
)
from tactix.config import Settings
from tactix.dashboard_query import DashboardQuery
from tactix.dashboard_query_filters import DashboardQueryFilters

ResultT = TypeVar("ResultT")


@dataclass
class DashboardUseCase:  # pylint: disable=too-many-instance-attributes
    filters_resolver: DashboardFiltersResolver = field(
        default_factory=DefaultDashboardFiltersResolver
    )
    cache_key_builder: DashboardCacheKeyBuilder = field(
        default_factory=DefaultDashboardCacheKeyBuilder
    )
    cache: DashboardCache = field(default_factory=DefaultDashboardCache)
    payload_fetcher: DashboardPayloadFetcher = field(default_factory=DefaultDashboardPayloadFetcher)
    stats_service: DashboardStatsService = field(default_factory=DefaultDashboardStatsService)
    version_provider: DashboardVersionProvider = field(
        default_factory=DefaultDashboardVersionProvider
    )
    dashboard_repository_factory: DashboardRepositoryFactory = field(
        default_factory=DefaultDashboardRepositoryFactory
    )
    raw_pgn_repository_factory: RawPgnRepositoryFactory = field(
        default_factory=DefaultRawPgnRepositoryFactory
    )
    uow_runner: UnitOfWorkRunner = field(default_factory=DuckDbUnitOfWorkRunner)
    settings_provider: SettingsProvider = field(default_factory=DefaultSettingsProvider)
    source_normalizer: SourceNormalizer = field(default_factory=DefaultSourceNormalizer)

    def get_dashboard(
        self,
        filters: DashboardQueryFilters,
        motif: str | None,
    ) -> dict[str, object]:
        start_datetime, end_datetime, normalized_source, settings = self.filters_resolver.resolve(
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
        cache_key = self.cache_key_builder.build(settings, query)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        payload = self.payload_fetcher.fetch(query, settings)
        self.cache.set(cache_key, payload)
        return payload

    def get_summary(
        self,
        filters: DashboardQueryFilters,
        db_name: str | None,
    ) -> dict[str, object]:
        start_datetime, end_datetime, normalized_source, settings = self.filters_resolver.resolve(
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
            lambda conn: self.dashboard_repository_factory.create(conn).fetch_pipeline_table_counts(
                query
            ),
        )
        response_source = "all" if normalized_source is None else normalized_source
        return {"source": response_source, "summary": summary}

    def get_motif_stats(self, filters: DashboardQueryFilters) -> dict[str, object]:
        return self._build_stats_payload(
            filters,
            self.stats_service.fetch_motif_stats,
            "motifs",
        )

    def get_trend_stats(self, filters: DashboardQueryFilters) -> dict[str, object]:
        return self._build_stats_payload(
            filters,
            self.stats_service.fetch_trend_stats,
            "trends",
        )

    def get_raw_pgns_summary(self, source: str | None) -> dict[str, object]:
        normalized_source = self.source_normalizer.normalize(source)
        settings = self.settings_provider.get_settings(source=normalized_source)
        active_source = normalized_source or settings.source
        return self._run_with_uow(
            settings,
            lambda conn: {
                "source": active_source,
                "summary": self.raw_pgn_repository_factory.create(conn).fetch_raw_pgns_summary(
                    source=active_source
                ),
            },
        )

    def _build_stats_payload(
        self,
        filters: DashboardQueryFilters,
        stats_fetcher: Callable[..., object],
        stats_key: str,
    ) -> dict[str, object]:
        start_datetime, end_datetime, normalized_source, settings = self.filters_resolver.resolve(
            filters
        )
        response_source = "all" if normalized_source is None else normalized_source

        def handler(conn):
            return {
                "source": response_source,
                "metrics_version": self.version_provider.fetch_version(conn),
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
        return self.uow_runner.run(settings.duckdb_path, handler)


def get_dashboard_use_case() -> DashboardUseCase:
    return DashboardUseCase()


__all__ = ["DashboardUseCase", "get_dashboard_use_case"]
