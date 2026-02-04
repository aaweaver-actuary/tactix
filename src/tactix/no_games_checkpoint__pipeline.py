"""Derive checkpoint values when no games are available."""

from __future__ import annotations

from tactix.config import Settings
from tactix.FetchContext import FetchContext


def _no_games_checkpoint(
    settings: Settings, backfill_mode: bool, fetch_context: FetchContext
) -> int | None:
    """Return the checkpoint value for no-games scenarios."""
    if backfill_mode or settings.source == "chesscom":
        return None
    return fetch_context.since_ms
