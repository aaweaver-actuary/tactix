"""Handle no-games scenarios in the sync pipeline."""

from __future__ import annotations

from tactix.build_no_games_payload__pipeline import _build_no_games_payload
from tactix.DailySyncStartContext import NoGamesContext
from tactix.define_pipeline_state__pipeline import logger
from tactix.emit_progress__pipeline import _emit_progress
from tactix.no_games_payload_contexts import build_no_games_payload_context


def _handle_no_games(
    context: NoGamesContext,
) -> dict[str, object]:
    """Return the no-games payload and emit progress updates."""
    logger.info(
        "No new games for source=%s at checkpoint=%s",
        context.settings.source,
        context.fetch_context.since_ms,
    )
    _emit_progress(
        context.progress,
        "no_games",
        source=context.settings.source,
        message="No new games to process",
    )
    return _build_no_games_payload(build_no_games_payload_context(context))
