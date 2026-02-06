"""Postgres repository adapter for read-only endpoints."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from tactix.config import Settings
from tactix.db.postgres_analysis_repository import fetch_analysis_tactics
from tactix.db.postgres_ops_repository import fetch_ops_events
from tactix.fetch_postgres_raw_pgns_summary import fetch_postgres_raw_pgns_summary
from tactix.get_postgres_status import get_postgres_status
from tactix.postgres_status import PostgresStatus


@dataclass(frozen=True)
class PostgresRepositoryDependencies:
    """Dependencies used by the Postgres repository."""

    get_status: Callable[[Settings], PostgresStatus]
    fetch_ops_events: Callable[[Settings, int], list[dict[str, Any]]]
    fetch_analysis_tactics: Callable[[Settings, int], list[dict[str, Any]]]
    fetch_raw_pgns_summary: Callable[[Settings], dict[str, Any]]


class PostgresRepository:
    """Encapsulates Postgres-backed read operations."""

    def __init__(
        self,
        settings: Settings,
        *,
        dependencies: PostgresRepositoryDependencies,
    ) -> None:
        self._settings = settings
        self._dependencies = dependencies

    def get_status(self) -> PostgresStatus:
        """Return the current Postgres status snapshot."""
        return self._dependencies.get_status(self._settings)

    def fetch_ops_events(self, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent ops events from Postgres."""
        return self._dependencies.fetch_ops_events(self._settings, limit)

    def fetch_analysis_tactics(self, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent analyzed tactics from Postgres."""
        return self._dependencies.fetch_analysis_tactics(self._settings, limit)

    def fetch_raw_pgns_summary(self) -> dict[str, Any]:
        """Fetch raw PGN summary data from Postgres."""
        return self._dependencies.fetch_raw_pgns_summary(self._settings)


def default_postgres_repository_dependencies() -> PostgresRepositoryDependencies:
    """Return default dependency wiring for Postgres repository operations."""
    return PostgresRepositoryDependencies(
        get_status=get_postgres_status,
        fetch_ops_events=fetch_ops_events,
        fetch_analysis_tactics=fetch_analysis_tactics,
        fetch_raw_pgns_summary=fetch_postgres_raw_pgns_summary,
    )
