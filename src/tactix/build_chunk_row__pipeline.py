from __future__ import annotations

from typing import cast

from tactix.config import Settings
from tactix.pipeline_state__pipeline import GameRow
from tactix.prepare_pgn__chess import extract_game_id, extract_last_timestamp_ms


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
