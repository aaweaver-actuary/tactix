"""Build DuckDB raw PGN upsert plans."""

from __future__ import annotations

from collections.abc import Mapping

import duckdb

from tactix._build_pgn_upsert_plan import _build_pgn_upsert_plan


def _build_raw_pgn_upsert_plan(
    conn: duckdb.DuckDBPyConnection,
    row: Mapping[str, object],
    game_id: str,
    source: str,
    latest_cache: dict[tuple[str, str], tuple[str | None, int]],
):
    """Return an upsert plan for a raw PGN row."""
    cached = latest_cache.get((game_id, source))
    if cached:
        latest_hash, latest_version = cached
    else:
        record = conn.execute(
            """
            SELECT pgn_hash, pgn_version
            FROM raw_pgns
            WHERE game_id = ? AND source = ?
            ORDER BY pgn_version DESC
            LIMIT 1
            """,
            [game_id, source],
        ).fetchone()
        if record:
            latest_hash = record[0]
            latest_version = int(record[1] or 0)
        else:
            latest_hash = None
            latest_version = 0
    return _build_pgn_upsert_plan(row, latest_hash, latest_version)
