"""Use-case dependency interfaces."""

# pylint: disable=too-few-public-methods,too-many-arguments

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol, TypeVar

from tactix.config import Settings
from tactix.dashboard_query import DashboardQuery
from tactix.dashboard_query_filters import DashboardQueryFilters
from tactix.ports.repositories import (
    DashboardRepository,
    PostgresRepository,
    RawPgnRepository,
    TacticRepository,
)

ResultT = TypeVar("ResultT")


class SettingsProvider(Protocol):
    """Provide settings for use-cases."""

    def get_settings(self, **kwargs: object) -> Settings:
        """Return resolved settings."""


class SourceNormalizer(Protocol):
    """Normalize source identifiers."""

    def normalize(self, source: str | None) -> str | None:
        """Return a normalized source name."""


class DateTimeCoercer(Protocol):
    """Coerce date values into datetimes."""

    def coerce(self, value: date | None, *, end_of_day: bool = False) -> datetime | None:
        """Return a coerced datetime value."""


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


class CacheRefresher(Protocol):
    """Refresh dashboard cache entries."""

    def refresh(self, sources: list[str | None]) -> None:
        """Trigger a refresh for the provided sources."""

    def sources_for_refresh(self, source: str | None) -> list[str | None]:
        """Return source list for cache refresh."""


class DashboardCache(Protocol):
    """Cache access for dashboard payloads."""

    def get(self, key: tuple[object, ...]) -> dict[str, object] | None:
        """Fetch cached payload if available."""

    def set(self, key: tuple[object, ...], payload: dict[str, object]) -> None:
        """Set cache payload."""


class DashboardCacheKeyBuilder(Protocol):
    """Build cache keys for dashboard payloads."""

    def build(self, settings: Settings, query: DashboardQuery) -> tuple[object, ...]:
        """Return a cache key."""


class DashboardPayloadFetcher(Protocol):
    """Fetch dashboard payloads."""

    def fetch(self, query: DashboardQuery, settings: Settings) -> dict[str, object]:
        """Return dashboard payload."""


class DashboardFiltersResolver(Protocol):
    """Resolve dashboard filters into query components."""

    def resolve(self, filters: DashboardQueryFilters) -> tuple[Any, Any, str | None, Settings]:
        """Return query time range, source, and settings."""


class DashboardRepositoryFactory(Protocol):
    """Create dashboard repositories."""

    def create(self, conn: Any) -> DashboardRepository:
        """Return a dashboard repository bound to the connection."""


class RawPgnRepositoryFactory(Protocol):
    """Create raw PGN repositories."""

    def create(self, conn: Any) -> RawPgnRepository:
        """Return a raw PGN repository bound to the connection."""


class TacticRepositoryFactory(Protocol):
    """Create tactic repositories."""

    def create(self, conn: Any) -> TacticRepository:
        """Return a tactic repository bound to the connection."""


class DashboardStatsService(Protocol):
    """Provide dashboard statistics."""

    def fetch_motif_stats(self, conn: Any, **kwargs: object) -> list[dict[str, object]]:
        """Fetch motif statistics."""

    def fetch_trend_stats(self, conn: Any, **kwargs: object) -> list[dict[str, object]]:
        """Fetch trend statistics."""


class DashboardVersionProvider(Protocol):
    """Provide the metrics version for dashboard stats."""

    def fetch_version(self, conn: Any) -> int:
        """Return the metrics version."""


class UnitOfWorkRunner(Protocol):
    """Run a unit-of-work boundary."""

    def run(self, db_path: Path, handler: Callable[[Any], ResultT]) -> ResultT:
        """Run a handler within a unit of work."""


class PostgresRepositoryProvider(Protocol):
    """Provide Postgres repository instances."""

    def create(self, settings: Settings) -> PostgresRepository:
        """Return a repository instance."""


class StatusSerializer(Protocol):
    """Serialize status payloads."""

    def serialize(self, status: object) -> dict[str, Any]:
        """Serialize status output."""


class Clock(Protocol):
    """Provide the current time."""

    def now(self) -> float:
        """Return current time in seconds."""
