"""Refresh the user_moves view to include played timestamps."""

from __future__ import annotations

import duckdb

from tactix.db.raw_pgns_queries import latest_raw_pgns_query


def _migration_add_user_moves_view(conn: duckdb.DuckDBPyConnection) -> None:
    """Create or replace the user_moves view with played_at data."""
    conn.execute(
        f"""
        CREATE OR REPLACE VIEW user_moves AS
        WITH latest_pgns AS (
            {latest_raw_pgns_query()}
        )
        SELECT
            p.position_id AS user_move_id,
            p.position_id,
            p.game_id,
            p.user,
            p.source,
            p.uci AS played_uci,
            p.san AS played_san,
            to_timestamp(latest_pgns.last_timestamp_ms / 1000) AS played_at,
            p.created_at
        FROM positions p
        LEFT JOIN latest_pgns
            ON latest_pgns.game_id = p.game_id
            AND latest_pgns.source = p.source
        WHERE COALESCE(p.user_to_move, TRUE) = TRUE
        """
    )


__all__ = ["_migration_add_user_moves_view"]
