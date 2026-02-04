"""Dataclass inputs for building chess game rows."""

# pylint: disable=invalid-name

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tactix.chess_clients.chess_game_row import ChessGameRow


@dataclass(frozen=True)
class GameRowInputs[T: "ChessGameRow"]:
    """Input fields used to build a chess game row."""

    game_id: str
    pgn: str
    last_timestamp_ms: int
    user: str
    source: str
    fetched_at: datetime | None = None
    model_cls: type[T] | None = None
