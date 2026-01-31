from __future__ import annotations

from tactix.chess_clients.chesscom_client import write_cursor as write_chesscom_cursor
from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import FetchContext, GameRow
from tactix.resolve_chesscom_last_timestamp__pipeline import _resolve_chesscom_last_timestamp


def _update_chesscom_checkpoint(
    settings: Settings,
    fetch_context: FetchContext,
    games: list[GameRow],
    last_timestamp_value: int,
) -> tuple[int | None, int]:
    write_chesscom_cursor(settings.checkpoint_path, fetch_context.next_cursor)
    last_timestamp_value = _resolve_chesscom_last_timestamp(
        fetch_context,
        games,
        last_timestamp_value,
    )
    return None, last_timestamp_value
