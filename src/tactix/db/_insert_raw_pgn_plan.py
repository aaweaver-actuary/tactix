"""Insert a raw PGN row from a plan."""

from __future__ import annotations

import duckdb

from tactix.db.RawPgnInsertInputs import RawPgnInsertInputs


def _insert_raw_pgn_plan(
    conn: duckdb.DuckDBPyConnection,
    inputs: RawPgnInsertInputs,
) -> None:
    """Insert a raw PGN row for a prepared plan."""
    metadata = inputs.plan.metadata
    conn.execute(
        """
        INSERT INTO raw_pgns (
            raw_pgn_id,
            game_id,
            user,
            source,
            fetched_at,
            pgn,
            pgn_hash,
            pgn_version,
            user_rating,
            time_control,
            ingested_at,
            last_timestamp_ms,
            cursor
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            inputs.raw_pgn_id,
            inputs.game_id,
            inputs.row.get("user"),
            inputs.source,
            inputs.plan.fetched_at,
            inputs.plan.pgn_text,
            inputs.plan.pgn_hash,
            inputs.plan.pgn_version,
            metadata.get("user_rating"),
            metadata.get("time_control"),
            inputs.plan.ingested_at,
            inputs.plan.last_timestamp_ms,
            inputs.plan.cursor,
        ],
    )
