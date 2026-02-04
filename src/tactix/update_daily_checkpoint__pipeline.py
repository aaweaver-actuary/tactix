"""Update daily checkpoints after sync."""

from __future__ import annotations

from tactix.config import Settings
from tactix.FetchContext import FetchContext
from tactix.GameRow import GameRow
from tactix.update_chesscom_checkpoint__pipeline import _update_chesscom_checkpoint
from tactix.update_lichess_checkpoint__pipeline import _update_lichess_checkpoint


def _update_daily_checkpoint(
    settings: Settings,
    backfill_mode: bool,
    fetch_context: FetchContext,
    games: list[GameRow],
    last_timestamp_value: int,
) -> tuple[int | None, int]:
    if backfill_mode:
        return None, last_timestamp_value
    if settings.source == "chesscom":
        return _update_chesscom_checkpoint(settings, fetch_context, games, last_timestamp_value)
    return _update_lichess_checkpoint(settings, fetch_context, games)
