"""Dashboard payload reader for DuckDB-backed data."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import duckdb

from tactix.dashboard_query import DashboardQuery


@dataclass(frozen=True)
class DuckDbDashboardFetchers:
    metrics: Callable[..., list[dict[str, object]]]
    recent_games: Callable[..., list[dict[str, object]]]
    recent_positions: Callable[..., list[dict[str, object]]]
    recent_tactics: Callable[..., list[dict[str, object]]]


@dataclass(frozen=True)
class DuckDbDashboardDependencies:
    resolve_query: Callable[..., DashboardQuery]
    clone_query: Callable[..., DashboardQuery]
    fetchers: DuckDbDashboardFetchers
    fetch_version: Callable[[duckdb.DuckDBPyConnection], int]
    init_schema: Callable[[duckdb.DuckDBPyConnection], None]


class DuckDbDashboardReader:
    """Build dashboard payloads from a DuckDB connection."""

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        *,
        user: str,
        dependencies: DuckDbDashboardDependencies,
    ) -> None:
        self._conn = conn
        self._user = user
        self._dependencies = dependencies

    def get_dashboard_payload(
        self,
        query: DashboardQuery | str | None = None,
        *,
        filters: DashboardQuery | None = None,
        **legacy: object,
    ) -> dict[str, object]:
        deps = self._dependencies
        resolved = deps.resolve_query(query, filters=filters, **legacy)
        deps.init_schema(self._conn)
        active_source = None if resolved.source in (None, "all") else resolved.source
        response_source = "all" if active_source is None else active_source
        metrics_query = deps.clone_query(resolved, source=active_source, motif=resolved.motif)
        non_motif_query = deps.clone_query(resolved, source=active_source, motif=None)
        tactics_query = deps.clone_query(resolved, source=active_source, motif=resolved.motif)
        fetchers = deps.fetchers
        return {
            "source": response_source,
            "user": self._user,
            "metrics": fetchers.metrics(self._conn, metrics_query),
            "recent_games": fetchers.recent_games(
                self._conn,
                non_motif_query,
                user=self._user,
            ),
            "positions": fetchers.recent_positions(
                self._conn,
                non_motif_query,
            ),
            "tactics": fetchers.recent_tactics(
                self._conn,
                tactics_query,
            ),
            "metrics_version": deps.fetch_version(self._conn),
        }

    def __call__(
        self,
        query: DashboardQuery | str | None = None,
        *,
        filters: DashboardQuery | None = None,
        **legacy: object,
    ) -> dict[str, object]:
        return self.get_dashboard_payload(query, filters=filters, **legacy)
