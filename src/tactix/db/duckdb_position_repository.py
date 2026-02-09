"""Position repository for DuckDB-backed storage."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import duckdb

from tactix.build_position_id__positions import _build_position_id
from tactix.db._rows_to_dicts import _rows_to_dicts


def _build_position_id_for_row(position: Mapping[str, object]) -> int:
    return _build_position_id(
        str(position.get("fen") or ""),
        str(position.get("side_to_move") or ""),
    )


def _build_position_insert_values(
    position: Mapping[str, object],
    position_id: int,
) -> list[object]:
    return [
        position_id,
        position.get("game_id"),
        position.get("user"),
        position.get("source"),
        position.get("fen"),
        position.get("ply"),
        position.get("move_number"),
        position.get("side_to_move"),
        position.get("user_to_move", True),
        position.get("uci"),
        position.get("san"),
        position.get("clock_seconds"),
        position.get("is_legal", True),
    ]


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
        ids: list[int] = []
        for pos in positions:
            position_id = _build_position_id_for_row(pos)
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
                    user_to_move,
                    uci,
                    san,
                    clock_seconds,
                    is_legal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _build_position_insert_values(pos, position_id),
            )
            ids.append(position_id)
        return ids


def default_position_dependencies() -> DuckDbPositionDependencies:
    """Return default dependency wiring for DuckDB position operations."""
    return DuckDbPositionDependencies(rows_to_dicts=_rows_to_dicts)
