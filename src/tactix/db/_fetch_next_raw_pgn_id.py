"""Fetch the next raw PGN identifier."""

from __future__ import annotations

import duckdb


def _fetch_next_raw_pgn_id(conn: duckdb.DuckDBPyConnection) -> int:
    """Return the next raw PGN id for inserts."""
    row = conn.execute("SELECT MAX(raw_pgn_id) FROM raw_pgns").fetchone()
    return int(row[0] or 0) if row else 0
