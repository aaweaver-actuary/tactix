"""Position repository for DuckDB-backed storage."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import duckdb

from tactix.db._rows_to_dicts import _rows_to_dicts


@dataclass(frozen=True)
class DuckDbPositionDependencies:
    """Dependencies used by the position repository."""

    rows_to_dicts: Callable[[duckdb.DuckDBPyRelation], list[dict[str, object]]]


class DuckDbPositionRepository:
    """Encapsulates position persistence and reads for DuckDB."""

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        *,
        dependencies: DuckDbPositionDependencies,
    ) -> None:
        self._conn = conn
        self._dependencies = dependencies

    def fetch_position_counts(
        self,
        game_ids: list[str],
        source: str | None,
    ) -> dict[str, int]:
        """Return position counts keyed by game id."""
        if not game_ids:
            return {}
        placeholders = ", ".join(["?"] * len(game_ids))
        params: list[object] = list(game_ids)
        sql = f"SELECT game_id, COUNT(*) FROM positions WHERE game_id IN ({placeholders})"
        if source:
            sql += " AND source = ?"
            params.append(source)
        sql += " GROUP BY game_id"
        rows = self._conn.execute(sql, params).fetchall()
        return {str(game_id): int(count) for game_id, count in rows}

    def fetch_positions_for_games(self, game_ids: list[str]) -> list[dict[str, object]]:
        """Return stored positions for the provided games."""
        if not game_ids:
            return []
        placeholders = ", ".join(["?"] * len(game_ids))
        result = self._conn.execute(
            f"SELECT * FROM positions WHERE game_id IN ({placeholders}) ORDER BY position_id",
            game_ids,
        )
        return self._dependencies.rows_to_dicts(result)

    def insert_positions(self, positions: list[Mapping[str, object]]) -> list[int]:
        """Insert position rows and return new ids."""
        if not positions:
            return []
        row = self._conn.execute("SELECT MAX(position_id) FROM positions").fetchone()
        next_id = int(row[0] or 0) if row else 0
        ids: list[int] = []
        for pos in positions:
            next_id += 1
            self._conn.execute(
                """
                INSERT INTO positions (
                    position_id,
                    game_id,
                    user,
                    source,
                    fen,
                    ply,
                    move_number,
                    side_to_move,
                    uci,
                    san,
                    clock_seconds,
                    is_legal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    next_id,
                    pos.get("game_id"),
                    pos.get("user"),
                    pos.get("source"),
                    pos.get("fen"),
                    pos.get("ply"),
                    pos.get("move_number"),
                    pos.get("side_to_move"),
                    pos.get("uci"),
                    pos.get("san"),
                    pos.get("clock_seconds"),
                    pos.get("is_legal", True),
                ],
            )
            ids.append(next_id)
        return ids


def default_position_dependencies() -> DuckDbPositionDependencies:
    """Return default dependency wiring for DuckDB position operations."""
    return DuckDbPositionDependencies(rows_to_dicts=_rows_to_dicts)
