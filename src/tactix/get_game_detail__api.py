from __future__ import annotations

from typing import Annotated

from fastapi import HTTPException, Query

from tactix.config import get_settings
from tactix.db.duckdb_store import fetch_game_detail, get_connection, init_schema
from tactix.normalize_source__source import _normalize_source


def game_detail(
    game_id: str,
    source: Annotated[str | None, Query()] = None,
) -> dict[str, object]:
    normalized_source = _normalize_source(source)
    settings = get_settings(source=normalized_source)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    payload = fetch_game_detail(
        conn,
        game_id=game_id,
        user=settings.user,
        source=normalized_source,
    )
    if not payload.get("pgn"):
        raise HTTPException(status_code=404, detail="Game not found")
    return payload
