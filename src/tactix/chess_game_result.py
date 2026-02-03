from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tactix.chess_player_color import ChessPlayerColor


class ChessGameResult(StrEnum):
    """
    Enumeration representing possible outcomes of a chess game.

    Attributes:
        WIN: Indicates a win.
        LOSS: Indicates a loss.
        DRAW: Indicates a draw.
        INCOMPLETE: Indicates the game is incomplete.

    Methods:
        from_str(result_str: str, color: ChessPlayerColor) -> ChessGameResult:
            Converts a result string and player color to a ChessGameResult enum value.
            Raises ValueError if the result string is invalid.
    """

    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    INCOMPLETE = "incomplete"

    @classmethod
    def from_str(cls, result_str: str, color: ChessPlayerColor) -> ChessGameResult:
        resolved = ChessPlayerColor.result_mapping(color).get(result_str.lower())
        if resolved is None:
            raise ValueError(f"Invalid game result string: {result_str}")
        return resolved
