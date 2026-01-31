from __future__ import annotations

from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import FetchContext


def _no_games_checkpoint(
    settings: Settings, backfill_mode: bool, fetch_context: FetchContext
) -> int | None:
    if backfill_mode or settings.source == "chesscom":
        return None
    return fetch_context.since_ms
