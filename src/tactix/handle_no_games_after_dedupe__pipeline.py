from __future__ import annotations

from tactix.build_no_games_after_dedupe_payload__pipeline import (
    _build_no_games_after_dedupe_payload,
)
from tactix.DailySyncStartContext import (
    NoGamesAfterDedupeContext,
)
from tactix.define_pipeline_state__pipeline import logger
from tactix.no_games_payload_contexts import build_no_games_after_dedupe_payload_context


def _handle_no_games_after_dedupe(
    context: NoGamesAfterDedupeContext,
) -> dict[str, object]:
    logger.info(
        "No new games to process after backfill dedupe for source=%s",
        context.settings.source,
    )
    return _build_no_games_after_dedupe_payload(
        build_no_games_after_dedupe_payload_context(context)
    )
