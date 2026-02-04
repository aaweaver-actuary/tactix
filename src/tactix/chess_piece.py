"""Chess piece data model."""

from __future__ import annotations

from dataclasses import dataclass

from tactix.chess_fen_char import ChessFenChar
from tactix.chess_piece_type import ChessPieceType
from tactix.chess_player_color import ChessPlayerColor


@dataclass
class ChessPiece:
    """
    Represents a chess piece with its color and type.

    Attributes:
        color (ChessPlayerColor): The color of the chess piece (e.g., white or black).
        piece (ChessPieceType): The type of the chess piece (e.g., pawn, knight, bishop, etc.).

    Methods:
        from_fen_char(fen_char: str) -> ChessPiece:
            Creates a ChessPiece instance from a FEN character.
            Raises ValueError if the FEN character is invalid.
    """

    color: ChessPlayerColor
    piece: ChessPieceType

    @classmethod
    def from_fen_char(cls, fen_char: str) -> ChessPiece:
        """Build a chess piece from a FEN character."""
        if not ChessFenChar.is_valid(fen_char):
            raise ValueError(f"Invalid FEN character: {fen_char}")
        color = ChessPlayerColor.from_fen_char(fen_char)
        piece_type = ChessPieceType.from_str(fen_char)
        return cls(color=color, piece=piece_type)
