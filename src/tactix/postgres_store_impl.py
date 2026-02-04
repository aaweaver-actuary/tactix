"""Postgres-backed store implementation."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from tactix.base_db_store import BaseDbStore
from tactix.dashboard_query import DashboardQuery
from tactix.postgres_status import PostgresStatus


class PostgresStore(BaseDbStore):
    """Postgres-backed store implementation."""

    def get_status(self) -> PostgresStatus:
        """Return the current Postgres status snapshot."""
        store_module = import_module("tactix.postgres_store")
        return store_module.get_postgres_status(self.settings)

    def fetch_ops_events(self, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent ops events from Postgres."""
        store_module = import_module("tactix.postgres_store")
        return store_module.fetch_ops_events(self.settings, limit=limit)

    def fetch_analysis_tactics(self, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent analyzed tactics from Postgres."""
        store_module = import_module("tactix.postgres_store")
        return store_module.fetch_analysis_tactics(self.settings, limit=limit)

    def fetch_raw_pgns_summary(self) -> dict[str, Any]:
        """Fetch raw PGN summary data from Postgres."""
        store_module = import_module("tactix.postgres_store")
        return store_module.fetch_postgres_raw_pgns_summary(self.settings)

    def get_dashboard_payload(
        self,
        query: DashboardQuery | str | None = None,
        *,
        filters: DashboardQuery | None = None,
        **legacy: object,
    ) -> dict[str, object]:
        """Raise because Postgres dashboard payloads are not supported."""
        raise NotImplementedError("Postgres dashboard payload is not supported")
