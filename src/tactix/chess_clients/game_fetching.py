"""Lichess game fetching helpers with retry support."""

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

from tactix.chess_clients.fetch_helpers import run_incremental_fetch
from tactix.config import Settings
from tactix.define_lichess_client__lichess_client import LichessClient
from tactix.define_lichess_client_context__lichess_client import LichessClientContext
from tactix.define_lichess_fetch_request__lichess_client import LichessFetchRequest
from tactix.utils.logger import Logger

log = Logger(__name__)


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
    before_sleep=before_sleep_log(log, logging.WARNING),
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

    context = LichessClientContext(settings=settings, logger=log)
    return LichessClient(context)._fetch_remote_games_with_refresh(since_ms, until_ms)


def fetch_incremental_games(
    settings: Settings, since_ms: int, until_ms: int | None = None
) -> list[dict]:
    """Fetch Lichess games incrementally.

    Args:
        settings: Settings for the request.
        since_ms: Minimum timestamp for included games.
        until_ms: Optional upper bound timestamp.

    Returns:
        List of game rows.
    """

    context = LichessClientContext(settings=settings, logger=log)
    request = LichessFetchRequest(since_ms=since_ms, until_ms=until_ms)
    return run_incremental_fetch(
        build_client=lambda: LichessClient(context),
        request=request,
    ).games


def _fetch_remote_games_once(
    settings: Settings, since_ms: int, until_ms: int | None = None
) -> list[dict]:
    """Fetch games from the remote API once.

    Args:
        settings: Settings for the request.
        since_ms: Minimum timestamp for included games.
        until_ms: Optional upper bound timestamp.

    Returns:
        Remote game rows.
    """

    context = LichessClientContext(settings=settings, logger=log)
    return LichessClient(context)._fetch_remote_games_once(since_ms, until_ms)
