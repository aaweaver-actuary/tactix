from __future__ import annotations

from tactix.build_no_games_after_dedupe_payload__pipeline import (
    _build_no_games_after_dedupe_payload,
)
from tactix.DailySyncStartContext import (
    NoGamesAfterDedupeContext,
    NoGamesAfterDedupePayloadContext,
)
from tactix.define_pipeline_state__pipeline import logger


def _handle_no_games_after_dedupe(
    context: NoGamesAfterDedupeContext,
) -> dict[str, object]:
    logger.info(
        "No new games to process after backfill dedupe for source=%s",
        context.settings.source,
    )
    return _build_no_games_after_dedupe_payload(
        NoGamesAfterDedupePayloadContext(
            settings=context.settings,
            conn=context.conn,
            backfill_mode=context.backfill_mode,
            fetch_context=context.fetch_context,
            last_timestamp_value=context.last_timestamp_value,
            games=context.games,
            window_filtered=context.window_filtered,
        )
    )
