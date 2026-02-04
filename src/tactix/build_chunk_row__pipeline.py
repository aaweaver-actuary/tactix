"""Build chunk rows for raw PGN persistence."""

from __future__ import annotations

from typing import cast

from tactix.config import Settings
from tactix.extract_game_id import extract_game_id
from tactix.extract_last_timestamp_ms import extract_last_timestamp_ms
from tactix.pipeline_state__pipeline import GameRow


def _build_chunk_row(row: GameRow, chunk: str, settings: Settings) -> GameRow:
    return cast(
        GameRow,
        {
            "game_id": extract_game_id(chunk),
            "user": row.get("user") or settings.user,
            "source": row.get("source") or settings.source,
            "fetched_at": row.get("fetched_at"),
            "pgn": chunk,
            "last_timestamp_ms": extract_last_timestamp_ms(chunk),
        },
    )
