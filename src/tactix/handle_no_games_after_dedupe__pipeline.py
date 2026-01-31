from __future__ import annotations

from tactix.build_no_games_after_dedupe_payload__pipeline import (
    _build_no_games_after_dedupe_payload,
)
from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import FetchContext, GameRow, logger


def _handle_no_games_after_dedupe(
    settings: Settings,
    conn,
    backfill_mode: bool,
    fetch_context: FetchContext,
    last_timestamp_value: int,
    games: list[GameRow],
    window_filtered: int,
) -> dict[str, object]:
    logger.info(
        "No new games to process after backfill dedupe for source=%s",
        settings.source,
    )
    return _build_no_games_after_dedupe_payload(
        settings,
        conn,
        backfill_mode,
        fetch_context,
        last_timestamp_value,
        games,
        window_filtered,
    )
