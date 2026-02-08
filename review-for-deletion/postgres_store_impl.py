"""Postgres-backed store implementation."""

from __future__ import annotations

from typing import Any

from tactix.dashboard_query import DashboardQuery
from tactix.db.postgres_repository import (
    PostgresRepository,
    default_postgres_repository_dependencies,
)
from tactix.define_base_db_store__db_store import BaseDbStore
from tactix.postgres_status import PostgresStatus


class PostgresStore(BaseDbStore):
    """Postgres-backed store implementation."""

    def _repository(self) -> PostgresRepository:
        return PostgresRepository(
            self.settings,
            dependencies=default_postgres_repository_dependencies(),
        )

    def get_status(self) -> PostgresStatus:
        """Return the current Postgres status snapshot."""
        return self._repository().get_status()

    def fetch_ops_events(self, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent ops events from Postgres."""
        return self._repository().fetch_ops_events(limit=limit)

    def fetch_analysis_tactics(self, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent analyzed tactics from Postgres."""
        return self._repository().fetch_analysis_tactics(limit=limit)

    def fetch_raw_pgns_summary(self) -> dict[str, Any]:
        """Fetch raw PGN summary data from Postgres."""
        return self._repository().fetch_raw_pgns_summary()

    def get_dashboard_payload(
        self,
        query: DashboardQuery | str | None = None,
        *,
        filters: DashboardQuery | None = None,
        **legacy: object,
    ) -> dict[str, object]:
        """Raise because Postgres dashboard payloads are not supported."""
        raise NotImplementedError("Postgres dashboard payload is not supported")
