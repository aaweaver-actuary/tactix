"""Add pipeline compatibility views and columns."""

from __future__ import annotations

import duckdb

from tactix.db.raw_pgns_queries import latest_raw_pgns_query


def _migration_add_pipeline_views(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure pipeline compatibility views and columns exist."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info('positions')").fetchall()}
    if "side_to_move" not in columns:
        conn.execute("ALTER TABLE positions ADD COLUMN side_to_move TEXT")
    if "user_to_move" not in columns:
        conn.execute("ALTER TABLE positions ADD COLUMN user_to_move BOOLEAN DEFAULT TRUE")
        conn.execute("UPDATE positions SET user_to_move = TRUE WHERE user_to_move IS NULL")

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
            t.tactic_piece,
            t.mate_type,
            t.best_san,
            t.explanation,
            t.eval_cp,
            t.created_at
        FROM tactics t
        INNER JOIN positions p ON p.position_id = t.position_id
        """
    )

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
            o.result,
            o.user_uci,
            o.eval_delta,
            o.created_at
        FROM tactic_outcomes o
        INNER JOIN opportunities opp ON opp.opportunity_id = o.tactic_id
        """
    )

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
            opp.tactic_piece,
            opp.mate_type,
            opp.best_san,
            opp.explanation,
            opp.eval_cp,
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


__all__ = ["_migration_add_pipeline_views"]
