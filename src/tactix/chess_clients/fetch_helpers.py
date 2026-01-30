from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tactix.chess_clients.base_chess_client import ChessFetchRequest, ChessFetchResult
from tactix.chess_clients.fixture_helpers import should_use_fixture_games
from tactix.pgn_utils import load_fixture_games


def should_use_fixture_data(token: str | None, use_fixture_when_no_token: bool) -> bool:
    return should_use_fixture_games(token, use_fixture_when_no_token)


__all__ = [
    "load_fixture_games",
    "run_incremental_fetch",
    "should_use_fixture_data",
]


def run_incremental_fetch(
    *,
    build_client: Callable[[], Any],
    request: ChessFetchRequest,
) -> ChessFetchResult:
    return build_client().fetch_incremental_games(request)
