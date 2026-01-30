from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from tactix.chess_clients.base_chess_client import ChessFetchRequest, ChessFetchResult
from tactix.chess_clients.fixture_helpers import (
    load_fixture_games_for_client,
    should_use_fixture_games,
)


def should_use_fixture_data(token: str | None, use_fixture_when_no_token: bool) -> bool:
    return should_use_fixture_games(token, use_fixture_when_no_token)


def load_fixture_games(
    *,
    fixture_path: Path,
    user: str,
    source: str,
    since_ms: int,
    until_ms: int | None = None,
    logger: logging.Logger | None = None,
    missing_message: str | None = None,
    loaded_message: str | None = None,
    coerce_rows: Callable[[Iterable[dict[str, Any]]], list[dict]] | None = None,
) -> list[dict]:
    games = load_fixture_games_for_client(
        fixture_path=fixture_path,
        user=user,
        source=source,
        since_ms=since_ms,
        until_ms=until_ms,
        logger=logger,
        missing_message=missing_message,
        loaded_message=loaded_message,
    )
    if coerce_rows:
        return coerce_rows(games)
    return list(games)


def run_incremental_fetch(
    *,
    build_client: Callable[[], Any],
    request: ChessFetchRequest,
) -> ChessFetchResult:
    return build_client().fetch_incremental_games(request)
