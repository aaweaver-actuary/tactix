"""Default dependency wiring for use-cases."""

from __future__ import annotations

import time as time_module
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, cast

from tactix._resolve_dashboard_filters import _resolve_dashboard_filters
from tactix.build_dashboard_cache_key__api_cache import _dashboard_cache_key
from tactix.coerce_date_to_datetime__datetime import _coerce_date_to_datetime
from tactix.config import Settings, get_settings
from tactix.dashboard_query import DashboardQuery
from tactix.dashboard_query_filters import DashboardQueryFilters
from tactix.db.dashboard_repository_provider import (
    dashboard_repository,
    fetch_motif_stats,
    fetch_trend_stats,
)
from tactix.db.duckdb_store import fetch_version, init_schema
from tactix.db.duckdb_unit_of_work import DuckDbUnitOfWork
from tactix.db.postgres_repository import (
    PostgresUnitOfWorkRepository,
    default_postgres_unit_of_work_dependencies,
)
from tactix.db.postgres_unit_of_work import PostgresUnitOfWork
from tactix.db.raw_pgn_repository_provider import raw_pgn_repository
from tactix.db.tactic_repository_provider import tactic_repository
from tactix.get_cached_dashboard_payload__api_cache import _get_cached_dashboard_payload
from tactix.list_sources_for_cache_refresh__api_cache import _sources_for_cache_refresh
from tactix.normalize_source__source import _normalize_source
from tactix.pipeline import get_dashboard_payload
from tactix.ports.repositories import (
    DashboardRepository,
    PostgresRepository,
    RawPgnRepository,
    TacticRepository,
)
from tactix.ports.unit_of_work import UnitOfWork
from tactix.refresh_dashboard_cache_async__api_cache import _refresh_dashboard_cache_async
from tactix.run_daily_game_sync__pipeline import run_daily_game_sync
from tactix.serialize_status import serialize_status
from tactix.set_dashboard_cache__api_cache import _set_dashboard_cache


@dataclass(frozen=True)
class DefaultSettingsProvider:
    """Default settings provider."""

    def get_settings(self, **kwargs: object) -> Settings:
        return get_settings(**kwargs)


@dataclass(frozen=True)
class DefaultSourceNormalizer:
    """Default source normalizer."""

    def normalize(self, source: str | None) -> str | None:
        return _normalize_source(source)


@dataclass(frozen=True)
class DefaultDateTimeCoercer:
    """Default datetime coercer."""

    def coerce(self, value: date | None, *, end_of_day: bool = False) -> datetime | None:
        return _coerce_date_to_datetime(value, end_of_day=end_of_day)


@dataclass(frozen=True)
class DefaultPipelineRunner:
    """Default pipeline runner."""

    def run(
        self,
        settings: Settings,
        *,
        source: str | None,
        window_start_ms: int | None,
        window_end_ms: int | None,
        profile: str | None,
    ) -> object:
        return run_daily_game_sync(
            settings,
            source=source,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            profile=profile,
        )


@dataclass(frozen=True)
class DefaultCacheRefresher:
    """Default cache refresher."""

    def refresh(self, sources: list[str | None]) -> None:
        _refresh_dashboard_cache_async(sources)

    def sources_for_refresh(self, source: str | None) -> list[str | None]:
        return _sources_for_cache_refresh(source)


@dataclass(frozen=True)
class DefaultDashboardCache:
    """Default dashboard cache implementation."""

    def get(self, key: tuple[object, ...]) -> dict[str, object] | None:
        return _get_cached_dashboard_payload(key)

    def set(self, key: tuple[object, ...], payload: dict[str, object]) -> None:
        _set_dashboard_cache(key, payload)


@dataclass(frozen=True)
class DefaultDashboardCacheKeyBuilder:
    """Default dashboard cache key builder."""

    def build(self, settings: Settings, query: DashboardQuery) -> tuple[object, ...]:
        return _dashboard_cache_key(settings, query)


@dataclass(frozen=True)
class DefaultDashboardPayloadFetcher:
    """Default dashboard payload fetcher."""

    def fetch(self, query: DashboardQuery, settings: Settings) -> dict[str, object]:
        return get_dashboard_payload(query, settings)


@dataclass(frozen=True)
class DefaultDashboardFiltersResolver:
    """Default dashboard filter resolver."""

    def resolve(self, filters: DashboardQueryFilters) -> tuple[Any, Any, str | None, Settings]:
        return _resolve_dashboard_filters(filters)


@dataclass(frozen=True)
class DefaultDashboardRepositoryFactory:
    """Default dashboard repository factory."""

    def create(self, conn: Any) -> DashboardRepository:
        return cast(DashboardRepository, dashboard_repository(conn))


@dataclass(frozen=True)
class DefaultRawPgnRepositoryFactory:
    """Default raw PGN repository factory."""

    def create(self, conn: Any) -> RawPgnRepository:
        return cast(RawPgnRepository, raw_pgn_repository(conn))


@dataclass(frozen=True)
class DefaultTacticRepositoryFactory:
    """Default tactic repository factory."""

    def create(self, conn: Any) -> TacticRepository:
        return cast(TacticRepository, tactic_repository(conn))


@dataclass(frozen=True)
class DefaultDashboardStatsService:
    """Default dashboard stats service."""

    motif_stats_fetcher: Callable[..., list[dict[str, object]]] = fetch_motif_stats
    trend_stats_fetcher: Callable[..., list[dict[str, object]]] = fetch_trend_stats

    def _fetch_stats(
        self,
        fetcher: Callable[..., list[dict[str, object]]],
        conn: Any,
        **kwargs: object,
    ) -> list[dict[str, object]]:
        return fetcher(conn, **kwargs)

    def fetch_motif_stats(self, conn: Any, **kwargs: object) -> list[dict[str, object]]:
        return self._fetch_stats(self.motif_stats_fetcher, conn, **kwargs)

    def fetch_trend_stats(self, conn: Any, **kwargs: object) -> list[dict[str, object]]:
        return self._fetch_stats(self.trend_stats_fetcher, conn, **kwargs)


@dataclass(frozen=True)
class DefaultDashboardVersionProvider:
    """Default version provider."""

    def fetch_version(self, conn: Any) -> int:
        return fetch_version(conn)


@dataclass(frozen=True)
class DuckDbUnitOfWorkRunner:
    """Unit-of-work runner for DuckDB."""

    unit_of_work_factory: Callable[[Path], UnitOfWork] = DuckDbUnitOfWork
    init_schema: Callable[[Any], None] = init_schema

    def run(self, db_path: Path, handler: Callable[[Any], Any]) -> Any:
        uow = self.unit_of_work_factory(db_path)
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


@dataclass(frozen=True)
class DefaultPostgresRepositoryProvider:
    """Default Postgres repository provider."""

    unit_of_work_factory: Callable[[Settings], UnitOfWork] = PostgresUnitOfWork
    dependencies: Any = field(default_factory=default_postgres_unit_of_work_dependencies)

    def create(self, settings: Settings) -> PostgresRepository:
        return PostgresUnitOfWorkRepository(
            settings,
            unit_of_work_factory=self.unit_of_work_factory,
            dependencies=self.dependencies,
        )


@dataclass(frozen=True)
class DefaultStatusSerializer:
    """Default status serializer."""

    def serialize(self, status: object) -> dict[str, Any]:
        return serialize_status(status)


@dataclass(frozen=True)
class DefaultClock:
    """Default system clock."""

    def now(self) -> float:
        return time_module.time()
