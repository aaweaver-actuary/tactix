"""Apply checkpoint updates when no games were deduped."""

from __future__ import annotations

from tactix.chess_clients.chesscom_client import write_cursor as write_chesscom_cursor
from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import FetchContext
from tactix.lichess_client import write_checkpoint


def _apply_no_games_dedupe_checkpoint(
    settings: Settings,
    backfill_mode: bool,
    fetch_context: FetchContext,
    last_timestamp_value: int,
) -> tuple[int | None, int]:
    if backfill_mode:
        return None, last_timestamp_value
    if settings.source == "chesscom":
        write_chesscom_cursor(settings.checkpoint_path, fetch_context.next_cursor)
        return None, last_timestamp_value
    checkpoint_value = max(fetch_context.since_ms, last_timestamp_value)
    write_checkpoint(settings.checkpoint_path, checkpoint_value)
    return checkpoint_value, checkpoint_value
