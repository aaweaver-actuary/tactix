"""Helpers for disabled raw PGN summaries."""

from typing import Any


def _disabled_raw_pgn_summary() -> dict[str, Any]:
    """Return the default disabled raw PGN summary payload."""
    return {
        "status": "disabled",
        "total_rows": 0,
        "distinct_games": 0,
        "latest_ingested_at": None,
        "sources": [],
    }
