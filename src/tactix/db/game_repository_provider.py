"""Factory helpers for DuckDB games table access."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import duckdb

from tactix.db.duckdb_game_repository import DuckDbGameRepository


def game_repository(conn: duckdb.DuckDBPyConnection) -> DuckDbGameRepository:
    """Return a DuckDbGameRepository bound to the provided connection."""
    return DuckDbGameRepository(conn)


def upsert_games(
    conn: duckdb.DuckDBPyConnection,
    rows: Iterable[Mapping[str, object]],
) -> int:
    """Insert or replace games rows."""
    return game_repository(conn).upsert_games(rows)


__all__ = ["game_repository", "upsert_games"]
