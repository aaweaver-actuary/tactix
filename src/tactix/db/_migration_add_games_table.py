"""Create a games table for canonical metadata."""

from __future__ import annotations

import duckdb


def _migration_add_games_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the games table and drop legacy views when needed."""
    conn.execute("DROP VIEW IF EXISTS games")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT,
            source TEXT,
            user TEXT,
            user_id TEXT,
            user_color TEXT,
            user_rating INTEGER,
            opp_rating INTEGER,
            result TEXT,
            time_control TEXT,
            played_at TIMESTAMP,
            pgn TEXT,
            fetched_at TIMESTAMP,
            ingested_at TIMESTAMP,
            last_timestamp_ms BIGINT,
            cursor TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS games_pk
        ON games (game_id, source)
        """
    )


__all__ = ["_migration_add_games_table"]
