"""API endpoint for DuckDB raw PGN summaries."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query

from tactix.config import get_settings
from tactix.db.duckdb_store import fetch_raw_pgns_summary, get_connection, init_schema
from tactix.normalize_source__source import _normalize_source


def raw_pgns_summary(
    source: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    """Return raw PGN summary payload for the given source."""
    normalized_source = _normalize_source(source)
    settings = get_settings(source=normalized_source)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    active_source = normalized_source or settings.source
    return {
        "source": active_source,
        "summary": fetch_raw_pgns_summary(conn, source=active_source),
    }
