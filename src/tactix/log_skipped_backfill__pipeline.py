from __future__ import annotations

from tactix.config import Settings
from tactix.pipeline_state__pipeline import GameRow, logger


def _log_skipped_backfill(settings: Settings, skipped_games: list[GameRow]) -> None:
    if skipped_games:
        logger.info(
            "Skipping %s historical games already processed for source=%s",
            len(skipped_games),
            settings.source,
        )
