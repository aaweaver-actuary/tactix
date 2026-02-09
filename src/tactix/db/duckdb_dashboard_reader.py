"""Dashboard payload reader for DuckDB-backed data."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import duckdb

from tactix.dashboard_query import DashboardQuery
from tactix.db.raw_pgns_queries import latest_raw_pgns_query

SOURCE_SYNC_WINDOW_DAYS = 90
SYNC_SOURCES = ("lichess", "chesscom")


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
            "source_sync": _fetch_source_sync(self._conn),
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


def _fetch_source_sync(conn: duckdb.DuckDBPyConnection) -> dict[str, object]:
    cutoff_ms = int(
        (datetime.now(tz=UTC) - timedelta(days=SOURCE_SYNC_WINDOW_DAYS)).timestamp() * 1000
    )
    rows = conn.execute(
        f"""
        WITH latest_pgns AS (
            {latest_raw_pgns_query()}
        )
        SELECT
            source,
            COUNT(DISTINCT game_id) AS games_played,
            MAX(last_timestamp_ms) AS latest_timestamp_ms
        FROM latest_pgns
        WHERE last_timestamp_ms IS NOT NULL AND last_timestamp_ms >= ?
        GROUP BY source
        ORDER BY source
        """,
        [cutoff_ms],
    ).fetchall()
    rows_by_source = {
        str(source): {
            "games_played": int(games_played or 0),
            "latest_timestamp_ms": latest_timestamp_ms,
        }
        for source, games_played, latest_timestamp_ms in rows
        if source
    }
    extra_sources = sorted(set(rows_by_source) - set(SYNC_SOURCES))
    ordered_sources = [*SYNC_SOURCES, *extra_sources]
    sources: list[dict[str, object]] = []
    for source in ordered_sources:
        row = rows_by_source.get(source, {})
        games_played = int(row.get("games_played") or 0)
        latest_timestamp_ms = row.get("latest_timestamp_ms")
        latest_played_at = _timestamp_ms_to_iso(latest_timestamp_ms)
        sources.append(
            {
                "source": source,
                "games_played": games_played,
                "synced": games_played > 0,
                "latest_played_at": latest_played_at,
            }
        )
    return {
        "window_days": SOURCE_SYNC_WINDOW_DAYS,
        "sources": sources,
    }


def _timestamp_ms_to_iso(value: object) -> str | None:
    if isinstance(value, (int, float)) and int(value) > 0:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC).isoformat()
    return None
