"""Factory helpers for DuckDB position repository access."""

from __future__ import annotations

from collections.abc import Mapping

import duckdb

from tactix.db.duckdb_position_repository import (
    DuckDbPositionRepository,
    default_position_dependencies,
)


def position_repository(conn: duckdb.DuckDBPyConnection) -> DuckDbPositionRepository:
    """Return a DuckDbPositionRepository bound to the provided connection."""
    return DuckDbPositionRepository(conn, dependencies=default_position_dependencies())


def fetch_position_counts(
    conn: duckdb.DuckDBPyConnection,
    game_ids: list[str],
    source: str | None,
) -> dict[str, int]:
    """Return position counts keyed by game id."""
    return position_repository(conn).fetch_position_counts(game_ids, source)


def fetch_positions_for_games(
    conn: duckdb.DuckDBPyConnection,
    game_ids: list[str],
) -> list[dict[str, object]]:
    """Return stored positions for the provided games."""
    return position_repository(conn).fetch_positions_for_games(game_ids)


def insert_positions(
    conn: duckdb.DuckDBPyConnection,
    positions: list[Mapping[str, object]],
) -> list[int]:
    """Insert position rows and return new ids."""
    return position_repository(conn).insert_positions(positions)
