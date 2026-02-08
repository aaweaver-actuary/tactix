"""Postgres repository adapter for read-only endpoints."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from tactix.config import Settings
from tactix.db.postgres_analysis_repository import (
    fetch_analysis_tactics,
    fetch_analysis_tactics_with_conn,
)
from tactix.db.postgres_ops_repository import fetch_ops_events, fetch_ops_events_with_conn
from tactix.db.postgres_raw_pgn_repository import (
    fetch_postgres_raw_pgns_summary,
    fetch_raw_pgns_summary_with_conn,
)
from tactix.db.postgres_unit_of_work import PostgresUnitOfWork
from tactix.get_postgres_status import get_postgres_status
from tactix.ports.unit_of_work import UnitOfWork
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


@dataclass(frozen=True)
class PostgresUnitOfWorkRepositoryDependencies:
    """Dependencies used by the Postgres unit-of-work repository."""

    get_status: Callable[[Settings], PostgresStatus]
    fetch_ops_events: Callable[[object | None, int], list[dict[str, Any]]]
    fetch_analysis_tactics: Callable[[object | None, Settings, int], list[dict[str, Any]]]
    fetch_raw_pgns_summary: Callable[[object | None, Settings], dict[str, Any]]


class PostgresUnitOfWorkRepository:
    """Encapsulates Postgres reads using a unit of work."""

    def __init__(
        self,
        settings: Settings,
        *,
        unit_of_work_factory: Callable[[Settings], UnitOfWork] = PostgresUnitOfWork,
        dependencies: PostgresUnitOfWorkRepositoryDependencies,
    ) -> None:
        self._settings = settings
        self._unit_of_work_factory = unit_of_work_factory
        self._dependencies = dependencies

    def get_status(self) -> PostgresStatus:
        """Return the current Postgres status snapshot."""
        return self._dependencies.get_status(self._settings)

    def fetch_ops_events(self, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent ops events from Postgres."""
        return self._run_with_uow(lambda conn: self._dependencies.fetch_ops_events(conn, limit))

    def fetch_analysis_tactics(self, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent analyzed tactics from Postgres."""
        return self._run_with_uow(
            lambda conn: self._dependencies.fetch_analysis_tactics(conn, self._settings, limit)
        )

    def fetch_raw_pgns_summary(self) -> dict[str, Any]:
        """Fetch raw PGN summary data from Postgres."""
        return self._run_with_uow(
            lambda conn: self._dependencies.fetch_raw_pgns_summary(conn, self._settings)
        )

    def _run_with_uow(self, handler: Callable[[object | None], Any]) -> Any:
        uow = self._unit_of_work_factory(self._settings)
        conn = uow.begin()
        try:
            result = handler(conn)
        except Exception:
            uow.rollback()
            raise
        else:
            uow.commit()
        finally:
            uow.close()
        return result


def default_postgres_unit_of_work_dependencies() -> PostgresUnitOfWorkRepositoryDependencies:
    """Return default dependency wiring for Postgres unit-of-work operations."""
    return PostgresUnitOfWorkRepositoryDependencies(
        get_status=get_postgres_status,
        fetch_ops_events=fetch_ops_events_with_conn,
        fetch_analysis_tactics=fetch_analysis_tactics_with_conn,
        fetch_raw_pgns_summary=fetch_raw_pgns_summary_with_conn,
    )
