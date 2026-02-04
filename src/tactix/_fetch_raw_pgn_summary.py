"""Fetch raw PGN summary metrics from the database."""

from collections.abc import Mapping
from typing import Any

from tactix.PGN_SCHEMA import PGN_SCHEMA


def _fetch_raw_pgn_summary(cur) -> tuple[list[Mapping[str, Any]], Mapping[str, Any]]:
    """Return per-source and total raw PGN summary data."""
    cur.execute(
        f"""
        SELECT
            source,
            COUNT(*) AS total_rows,
            COUNT(DISTINCT game_id) AS distinct_games,
            MAX(ingested_at) AS latest_ingested_at
        FROM {PGN_SCHEMA}.raw_pgns
        GROUP BY source
        ORDER BY source
        """
    )
    sources = cur.fetchall()
    cur.execute(
        f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT game_id) AS distinct_games,
            MAX(ingested_at) AS latest_ingested_at
        FROM {PGN_SCHEMA}.raw_pgns
        """
    )
    totals = cur.fetchone() or {}
    return sources, totals if isinstance(totals, Mapping) else {}
