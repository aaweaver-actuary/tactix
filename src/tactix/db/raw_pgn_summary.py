"""Helpers for raw PGN summary payloads."""

from collections.abc import Iterable, Mapping
from typing import Any


def coerce_raw_pgn_summary_rows(
    rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Coerce summary rows into dictionaries."""
    return [dict(row) for row in rows]


def build_raw_pgn_summary_sources(
    rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build source summaries for raw PGN payloads."""
    return coerce_raw_pgn_summary_rows(rows)


def build_raw_pgn_summary_payload(
    *,
    sources: Iterable[Mapping[str, Any]],
    totals: Mapping[str, Any],
    status: str = "ok",
) -> dict[str, Any]:
    """Build the raw PGN summary payload."""
    return {
        "status": status,
        "total_rows": totals.get("total_rows", 0),
        "distinct_games": totals.get("distinct_games", 0),
        "latest_ingested_at": totals.get("latest_ingested_at"),
        "sources": build_raw_pgn_summary_sources(sources),
    }
