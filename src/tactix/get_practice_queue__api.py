"""API endpoint to fetch the practice queue."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query

from tactix.config import get_settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.tactic_repository_provider import tactic_repository
from tactix.normalize_source__source import _normalize_source


def practice_queue(
    source: Annotated[str | None, Query()] = None,
    include_failed_attempt: bool = Query(False),  # noqa: B008
    limit: int = Query(20, ge=1, le=200),  # noqa: B008
) -> dict[str, object]:
    """Fetch a practice queue payload for the requested source."""
    normalized_source = _normalize_source(source)
    settings = get_settings(source=normalized_source)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    queue = tactic_repository(conn).fetch_practice_queue(
        limit=limit,
        source=normalized_source or settings.source,
        include_failed_attempt=include_failed_attempt,
    )
    return {
        "source": normalized_source or settings.source,
        "include_failed_attempt": include_failed_attempt,
        "items": queue,
    }
