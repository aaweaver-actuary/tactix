"""Typed keyword arguments for building PGN contexts."""

# pylint: disable=invalid-name

from __future__ import annotations

from typing import TypedDict


class PgnContextKwargs(TypedDict, total=False):
    """Keyword arguments accepted by `PgnContext`."""

    pgn: str
    user: str
    source: str
    game_id: str | None
    side_to_move_filter: str | None
