"""Use-case dependency interfaces and default implementations."""

from __future__ import annotations

import time as time_module
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, TypeVar

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
from tactix.ports.repositories import DashboardRepository, RawPgnRepository, TacticRepository
from tactix.ports.unit_of_work import UnitOfWork
from tactix.refresh_dashboard_cache_async__api_cache import _refresh_dashboard_cache_async
from tactix.run_daily_game_sync__pipeline import run_daily_game_sync
from tactix.serialize_status import serialize_status
from tactix.set_dashboard_cache__api_cache import _set_dashboard_cache

ResultT = TypeVar("ResultT")


class SettingsProvider(Protocol):
    """Provide settings for use-cases."""

    def get_settings(self, **kwargs: object) -> Settings:
        """Return resolved settings."""


@dataclass(frozen=True)
class DefaultSettingsProvider:
    """Default settings provider."""

    def get_settings(self, **kwargs: object) -> Settings:
        return get_settings(**kwargs)


class SourceNormalizer(Protocol):
    """Normalize source identifiers."""

    def normalize(self, source: str | None) -> str | None:
        """Return a normalized source name."""


@dataclass(frozen=True)
class DefaultSourceNormalizer:
    """Default source normalizer."""

    def normalize(self, source: str | None) -> str | None:
        return _normalize_source(source)


class DateTimeCoercer(Protocol):
    """Coerce date values into datetimes."""

    def coerce(self, value: object, *, end_of_day: bool = False) -> Any:
        """Return a coerced datetime value."""


@dataclass(frozen=True)
class DefaultDateTimeCoercer:
    """Default datetime coercer."""

    def coerce(self, value: object, *, end_of_day: bool = False) -> Any:
        return _coerce_date_to_datetime(value, end_of_day=end_of_day)


class PipelineRunner(Protocol):
    """Run the pipeline for a settings payload."""

    def run(
        self,
        settings: Settings,
        *,
        source: str | None,
        window_start_ms: int | None,
        window_end_ms: int | None,
        profile: str | None,
    ) -> object:
        """Run the pipeline."""


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


class CacheRefresher(Protocol):
    """Refresh dashboard cache entries."""

    def refresh(self, sources: list[str | None]) -> None:
        """Trigger a refresh for the provided sources."""

    def sources_for_refresh(self, source: str | None) -> list[str | None]:
        """Return source list for cache refresh."""


@dataclass(frozen=True)
class DefaultCacheRefresher:
    """Default cache refresher."""

    def refresh(self, sources: list[str | None]) -> None:
        _refresh_dashboard_cache_async(sources)

    def sources_for_refresh(self, source: str | None) -> list[str | None]:
        return _sources_for_cache_refresh(source)


class DashboardCache(Protocol):
    """Cache access for dashboard payloads."""

    def get(self, key: tuple[object, ...]) -> dict[str, object] | None:
        """Fetch cached payload if available."""

    def set(self, key: tuple[object, ...], payload: dict[str, object]) -> None:
        """Set cache payload."""


@dataclass(frozen=True)
class DefaultDashboardCache:
    """Default dashboard cache implementation."""

    def get(self, key: tuple[object, ...]) -> dict[str, object] | None:
        return _get_cached_dashboard_payload(key)

    def set(self, key: tuple[object, ...], payload: dict[str, object]) -> None:
        _set_dashboard_cache(key, payload)


class DashboardCacheKeyBuilder(Protocol):
    """Build cache keys for dashboard payloads."""

    def build(self, settings: Settings, query: DashboardQuery) -> tuple[object, ...]:
        """Return a cache key."""


@dataclass(frozen=True)
class DefaultDashboardCacheKeyBuilder:
    """Default dashboard cache key builder."""

    def build(self, settings: Settings, query: DashboardQuery) -> tuple[object, ...]:
        return _dashboard_cache_key(settings, query)


class DashboardPayloadFetcher(Protocol):
    """Fetch dashboard payloads."""

    def fetch(self, query: DashboardQuery, settings: Settings) -> dict[str, object]:
        """Return dashboard payload."""


@dataclass(frozen=True)
class DefaultDashboardPayloadFetcher:
    """Default dashboard payload fetcher."""

    def fetch(self, query: DashboardQuery, settings: Settings) -> dict[str, object]:
        return get_dashboard_payload(query, settings)


class DashboardFiltersResolver(Protocol):
    """Resolve dashboard filters into query components."""

    def resolve(self, filters: DashboardQueryFilters) -> tuple[Any, Any, str | None, Settings]:
        """Return query time range, source, and settings."""


@dataclass(frozen=True)
class DefaultDashboardFiltersResolver:
    """Default dashboard filter resolver."""

    def resolve(self, filters: DashboardQueryFilters) -> tuple[Any, Any, str | None, Settings]:
        return _resolve_dashboard_filters(filters)


class DashboardRepositoryFactory(Protocol):
    """Create dashboard repositories."""

    def create(self, conn: Any) -> DashboardRepository:
        """Return a dashboard repository bound to the connection."""


@dataclass(frozen=True)
class DefaultDashboardRepositoryFactory:
    """Default dashboard repository factory."""

    def create(self, conn: Any) -> DashboardRepository:
        return dashboard_repository(conn)


class RawPgnRepositoryFactory(Protocol):
    """Create raw PGN repositories."""

    def create(self, conn: Any) -> RawPgnRepository:
        """Return a raw PGN repository bound to the connection."""


@dataclass(frozen=True)
class DefaultRawPgnRepositoryFactory:
    """Default raw PGN repository factory."""

    def create(self, conn: Any) -> RawPgnRepository:
        return raw_pgn_repository(conn)


class TacticRepositoryFactory(Protocol):
    """Create tactic repositories."""

    def create(self, conn: Any) -> TacticRepository:
        """Return a tactic repository bound to the connection."""


@dataclass(frozen=True)
class DefaultTacticRepositoryFactory:
    """Default tactic repository factory."""

    def create(self, conn: Any) -> TacticRepository:
        return tactic_repository(conn)


class DashboardStatsService(Protocol):
    """Provide dashboard statistics."""

    def fetch_motif_stats(self, conn: Any, **kwargs: object) -> list[dict[str, object]]:
        """Fetch motif statistics."""

    def fetch_trend_stats(self, conn: Any, **kwargs: object) -> list[dict[str, object]]:
        """Fetch trend statistics."""


@dataclass(frozen=True)
class DefaultDashboardStatsService:
    """Default dashboard stats service."""

    def fetch_motif_stats(self, conn: Any, **kwargs: object) -> list[dict[str, object]]:
        return fetch_motif_stats(conn, **kwargs)

    def fetch_trend_stats(self, conn: Any, **kwargs: object) -> list[dict[str, object]]:
        return fetch_trend_stats(conn, **kwargs)


class DashboardVersionProvider(Protocol):
    """Provide the metrics version for dashboard stats."""

    def fetch_version(self, conn: Any) -> int:
        """Return the metrics version."""


@dataclass(frozen=True)
class DefaultDashboardVersionProvider:
    """Default version provider."""

    def fetch_version(self, conn: Any) -> int:
        return fetch_version(conn)


class UnitOfWorkRunner(Protocol):
    """Run a unit-of-work boundary."""

    def run(self, db_path: Path, handler: Callable[[Any], ResultT]) -> ResultT:
        """Run a handler within a unit of work."""


@dataclass(frozen=True)
class DuckDbUnitOfWorkRunner:
    """Unit-of-work runner for DuckDB."""

    unit_of_work_factory: Callable[[Path], UnitOfWork] = DuckDbUnitOfWork
    init_schema: Callable[[Any], None] = init_schema

    def run(self, db_path: Path, handler: Callable[[Any], ResultT]) -> ResultT:
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


class PostgresRepositoryProvider(Protocol):
    """Provide Postgres repository instances."""

    def create(self, settings: Settings) -> PostgresUnitOfWorkRepository:
        """Return a repository instance."""


@dataclass(frozen=True)
class DefaultPostgresRepositoryProvider:
    """Default Postgres repository provider."""

    unit_of_work_factory: Callable[[Settings], UnitOfWork] = PostgresUnitOfWork
    dependencies: Any = field(default_factory=default_postgres_unit_of_work_dependencies)

    def create(self, settings: Settings) -> PostgresUnitOfWorkRepository:
        return PostgresUnitOfWorkRepository(
            settings,
            unit_of_work_factory=self.unit_of_work_factory,
            dependencies=self.dependencies,
        )


class StatusSerializer(Protocol):
    """Serialize status payloads."""

    def serialize(self, status: object) -> dict[str, Any]:
        """Serialize status output."""


@dataclass(frozen=True)
class DefaultStatusSerializer:
    """Default status serializer."""

    def serialize(self, status: object) -> dict[str, Any]:
        return serialize_status(status)


class Clock(Protocol):
    """Provide the current time."""

    def now(self) -> float:
        """Return current time in seconds."""


@dataclass(frozen=True)
class DefaultClock:
    """Default system clock."""

    def now(self) -> float:
        return time_module.time()
