"""Fetch remote Lichess games with retries."""

# pylint: disable=protected-access

from __future__ import annotations

import logging

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tactix.config import Settings
from tactix.utils.logger import get_logger

logger = get_logger(__name__)


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def _fetch_remote_games(
    settings: Settings, since_ms: int, until_ms: int | None = None
) -> list[dict]:
    """Fetch games from the remote API with retry.

    Args:
        settings: Settings for the request.
        since_ms: Minimum timestamp for included games.
        until_ms: Optional upper bound timestamp.

    Returns:
        Remote game rows.
    """

    from tactix.chess_clients import game_fetching  # noqa: PLC0415

    return game_fetching._fetch_remote_games(settings, since_ms, until_ms)
