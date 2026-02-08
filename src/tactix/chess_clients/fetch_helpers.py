"""Helpers for chess client fetch flows."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tactix.chess_clients.base_chess_client import ChessFetchRequest, ChessFetchResult
from tactix.chess_clients.fixture_helpers import should_use_fixture_games
from tactix.load_fixture_games import load_fixture_games


def should_use_fixture_data(token: str | None, use_fixture_when_no_token: bool) -> bool:
    """Return whether fixture data should be used for a fetch."""
    return should_use_fixture_games(token, use_fixture_when_no_token)


def use_fixture_games(token: str | None, use_fixture_when_no_token: bool) -> bool:
    """Alias for fixture usage decision."""
    return should_use_fixture_data(token, use_fixture_when_no_token)


__all__ = [
    "load_fixture_games",
    "run_incremental_fetch",
    "should_use_fixture_data",
    "use_fixture_games",
]


def run_incremental_fetch(
    *,
    build_client: Callable[[], Any],
    request: ChessFetchRequest,
) -> ChessFetchResult:
    """Run an incremental fetch using a constructed client."""
    return build_client().fetch_incremental_games(request)
