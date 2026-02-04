from __future__ import annotations

from typing import TypedDict


class PgnContextKwargs(TypedDict):
    pgn: str
    user: str
    source: str
    game_id: str | None
    side_to_move_filter: str | None
