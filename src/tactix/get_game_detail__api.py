"""API handler for game detail retrieval."""

from __future__ import annotations

from typing import Annotated

from fastapi import HTTPException, Query

from tactix.config import get_settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.tactic_repository_provider import tactic_repository
from tactix.normalize_source__source import _normalize_source


def game_detail(
    game_id: str,
    source: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    """Return game detail payload for a game id."""
    normalized_source = _normalize_source(source)
    settings = get_settings(source=normalized_source)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    payload = tactic_repository(conn).fetch_game_detail(
        game_id,
        settings.user,
        normalized_source,
    )
    if not payload.get("pgn"):
        raise HTTPException(status_code=404, detail="Game not found")
    return payload
