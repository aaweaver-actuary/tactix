"""DuckDB repository for canonical game metadata."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import duckdb


class DuckDbGameRepository:  # pylint: disable=too-few-public-methods
    """Persist canonical game metadata rows in DuckDB."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def upsert_games(self, rows: Iterable[Mapping[str, object]]) -> int:
        """Insert or replace games rows and return inserted count."""
        rows_list = list(rows)
        if not rows_list:
            return 0
        self._conn.executemany(
            """
            INSERT OR REPLACE INTO games (
                game_id,
                source,
                user,
                user_id,
                user_color,
                user_rating,
                opp_rating,
                result,
                time_control,
                played_at,
                pgn,
                fetched_at,
                ingested_at,
                last_timestamp_ms,
                cursor
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row.get("game_id"),
                    row.get("source"),
                    row.get("user"),
                    row.get("user_id"),
                    row.get("user_color"),
                    row.get("user_rating"),
                    row.get("opp_rating"),
                    row.get("result"),
                    row.get("time_control"),
                    row.get("played_at"),
                    row.get("pgn"),
                    row.get("fetched_at"),
                    row.get("ingested_at"),
                    row.get("last_timestamp_ms"),
                    row.get("cursor"),
                )
                for row in rows_list
            ],
        )
        return len(rows_list)


__all__ = ["DuckDbGameRepository"]
