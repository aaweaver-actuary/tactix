"""API endpoint for the next practice item."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query

from tactix.config import get_settings
from tactix.db.duckdb_store import fetch_practice_queue, get_connection, init_schema
from tactix.normalize_source__source import _normalize_source


def practice_next(
    source: Annotated[str | None, Query()] = None,
    include_failed_attempt: bool = Query(False),  # noqa: B008
) -> dict[str, object]:
    """Fetch the next practice item for the requested source."""
    normalized_source = _normalize_source(source)
    settings = get_settings(source=normalized_source)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    items = fetch_practice_queue(
        conn,
        limit=1,
        source=normalized_source or settings.source,
        include_failed_attempt=include_failed_attempt,
        exclude_seen=True,
    )
    return {
        "source": normalized_source or settings.source,
        "include_failed_attempt": include_failed_attempt,
        "item": items[0] if items else None,
    }
