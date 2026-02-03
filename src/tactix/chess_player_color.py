from __future__ import annotations

from enum import Enum

import chess

from tactix.chess_game_result import ChessGameResult


class ChessPlayerColor(Enum):
    """Enum representing the color of a chess player, with
    utility methods for conversion and result mapping.

    Attributes:
        WHITE: Represents the white player (corresponds to chess.WHITE).
        BLACK: Represents the black player (corresponds to chess.BLACK).

    Methods:
        from_str(color_str: str) -> ChessPlayerColor:
            Converts a string to the corresponding ChessPlayerColor enum value.
            Raises ValueError for input besides ("white", "w", "black", "b").

        from_fen_char(fen_char: str) -> ChessPlayerColor:
            Determines player color from a FEN character (uppercase for white, lowercase for black).

        is_white() -> bool:
            Returns True if the color is white.

        is_black() -> bool:
            Returns True if the color is black.

        result_mapping() -> dict[str, ChessGameResult]:
            Returns a mapping from result strings:
                ("win", "loss", "draw", "incomplete", "1-0", "0-1", "1/2-1/2")
            to ChessGameResult values, adjusted for the player's color.
    """

    WHITE = chess.WHITE
    BLACK = chess.BLACK

    @classmethod
    def from_str(cls, color_str: str) -> ChessPlayerColor:
        color_str = color_str.lower()
        if color_str in ["white", "w"]:
            return cls.WHITE
        if color_str in ["black", "b"]:
            return cls.BLACK
        raise ValueError(f"Invalid color string: {color_str}")

    @classmethod
    def from_fen_char(cls, fen_char: str) -> ChessPlayerColor:
        if fen_char.isupper():
            return cls.WHITE
        return cls.BLACK

    def is_white(self) -> bool:
        return self == ChessPlayerColor.WHITE

    def is_black(self) -> bool:
        return self == ChessPlayerColor.BLACK

    @property
    def _base_result_mapping(self) -> dict[str, ChessGameResult]:
        return {
            "win": ChessGameResult.WIN,
            "loss": ChessGameResult.LOSS,
            "draw": ChessGameResult.DRAW,
            "incomplete": ChessGameResult.INCOMPLETE,
        }

    @property
    def _result_mapping_if_white(self) -> dict[str, ChessGameResult]:
        return {
            **self._base_result_mapping,
            "1-0": ChessGameResult.WIN,
            "0-1": ChessGameResult.LOSS,
            "1/2-1/2": ChessGameResult.DRAW,
        }

    @property
    def _result_mapping_if_black(self) -> dict[str, ChessGameResult]:
        return {
            **self._base_result_mapping,
            "1-0": ChessGameResult.LOSS,
            "0-1": ChessGameResult.WIN,
            "1/2-1/2": ChessGameResult.DRAW,
        }

    def result_mapping(self) -> dict[str, ChessGameResult]:
        if self.is_white():
            return self._result_mapping_if_white
        return self._result_mapping_if_black
