"""Add pipeline compatibility views and columns."""

from __future__ import annotations

import duckdb

from tactix.db._migration_add_user_moves_view import _migration_add_user_moves_view
from tactix.db.raw_pgns_queries import latest_raw_pgns_query


def _ensure_missing_columns(
    conn: duckdb.DuckDBPyConnection,
    columns: set[str],
    additions: dict[str, str],
) -> None:
    for name, statement in additions.items():
        if name not in columns:
            conn.execute(statement)


def _ensure_positions_columns(conn: duckdb.DuckDBPyConnection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info('positions')").fetchall()}
    has_user_to_move = "user_to_move" in columns
    _ensure_missing_columns(
        conn,
        columns,
        {
            "side_to_move": "ALTER TABLE positions ADD COLUMN side_to_move TEXT",
            "user_to_move": "ALTER TABLE positions ADD COLUMN user_to_move BOOLEAN DEFAULT TRUE",
        },
    )
    if not has_user_to_move:
        conn.execute("UPDATE positions SET user_to_move = TRUE WHERE user_to_move IS NULL")


def _ensure_tactics_columns(conn: duckdb.DuckDBPyConnection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info('tactics')").fetchall()}
    _ensure_missing_columns(
        conn,
        columns,
        {
            "target_piece": "ALTER TABLE tactics ADD COLUMN target_piece TEXT",
            "target_square": "ALTER TABLE tactics ADD COLUMN target_square TEXT",
            "best_line_uci": "ALTER TABLE tactics ADD COLUMN best_line_uci TEXT",
            "engine_depth": "ALTER TABLE tactics ADD COLUMN engine_depth INTEGER",
            "confidence": "ALTER TABLE tactics ADD COLUMN confidence TEXT",
        },
    )


def _create_games_view(conn: duckdb.DuckDBPyConnection) -> None:
    row = conn.execute(
        "SELECT table_type FROM information_schema.tables WHERE table_name = 'games'"
    ).fetchone()
    if row and row[0] == "BASE TABLE":
        return
    conn.execute(
        f"""
        CREATE OR REPLACE VIEW games AS
        WITH latest_pgns AS (
            {latest_raw_pgns_query()}
        )
        SELECT
            game_id,
            user,
            source,
            pgn,
            pgn_hash,
            pgn_version,
            time_control,
            user_rating,
            fetched_at,
            ingested_at,
            last_timestamp_ms,
            cursor,
            to_timestamp(last_timestamp_ms / 1000) AS played_at
        FROM latest_pgns
        """
    )


def _create_opportunities_view(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE OR REPLACE VIEW opportunities AS
        SELECT
            t.tactic_id AS opportunity_id,
            t.position_id,
            p.game_id,
            p.user,
            p.source,
            t.motif,
            t.severity,
            t.best_uci,
            t.best_line_uci,
            t.tactic_piece,
            t.mate_type,
            t.best_san,
            t.explanation,
            t.target_piece,
            t.target_square,
            t.eval_cp,
            t.engine_depth,
            t.confidence,
            t.created_at
        FROM tactics t
        INNER JOIN positions p ON p.position_id = t.position_id
        """
    )


def _create_conversions_view(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE OR REPLACE VIEW conversions AS
        SELECT
            o.outcome_id AS conversion_id,
            o.tactic_id AS opportunity_id,
            opp.position_id,
            opp.game_id,
            opp.user,
            opp.source,
            opp.motif,
            opp.mate_type,
            o.result,
            o.user_uci,
            o.eval_delta,
            o.result = 'found' AS converted,
            CASE
                WHEN opp.motif = 'hanging_piece'
                    AND o.result = 'found'
                    AND opp.target_square IS NOT NULL
                    AND substr(o.user_uci, 3, 2) = opp.target_square
                THEN 'captured_target'
                WHEN opp.motif = 'mate'
                    AND o.result = 'found'
                    AND opp.best_line_uci IS NOT NULL
                    AND split_part(opp.best_line_uci, ' ', 1) = o.user_uci
                THEN 'played_mate_line'
            END AS conversion_reason,
            o.created_at
        FROM tactic_outcomes o
        INNER JOIN opportunities opp ON opp.opportunity_id = o.tactic_id
        """
    )


def _create_practice_queue_view(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE OR REPLACE VIEW practice_queue AS
        SELECT
            opp.opportunity_id,
            conv.conversion_id,
            conv.result,
            opp.position_id,
            opp.game_id,
            opp.user,
            opp.source,
            opp.motif,
            opp.severity,
            opp.best_uci,
            opp.best_line_uci,
            opp.tactic_piece,
            opp.mate_type,
            opp.best_san,
            opp.explanation,
            opp.eval_cp,
            opp.target_piece,
            opp.target_square,
            opp.engine_depth,
            opp.confidence,
            p.fen,
            p.uci AS position_uci,
            p.san,
            p.ply,
            p.move_number,
            p.side_to_move,
            p.clock_seconds,
            opp.created_at AS opportunity_created_at,
            conv.created_at AS conversion_created_at
        FROM conversions conv
        INNER JOIN opportunities opp ON opp.opportunity_id = conv.opportunity_id
        INNER JOIN positions p ON p.position_id = opp.position_id
        WHERE conv.result = 'missed'
        """
    )


def _migration_add_pipeline_views(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure pipeline compatibility views and columns exist."""
    _ensure_positions_columns(conn)
    _ensure_tactics_columns(conn)
    _create_games_view(conn)
    _migration_add_user_moves_view(conn)
    _create_opportunities_view(conn)
    _create_conversions_view(conn)
    _create_practice_queue_view(conn)


__all__ = ["_migration_add_pipeline_views"]
