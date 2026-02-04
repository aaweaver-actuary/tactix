"""Piece type helpers for chess models."""

from __future__ import annotations

from enum import StrEnum

import chess


class ChessPieceType(StrEnum):
    """
    An enumeration representing the types of chess pieces.

    Attributes:
        PAWN (str): Represents a pawn piece.
        KNIGHT (str): Represents a knight piece.
        BISHOP (str): Represents a bishop piece.
        ROOK (str): Represents a rook piece.
        QUEEN (str): Represents a queen piece.
        KING (str): Represents a king piece.

    Methods:
        from_str(string: str) -> ChessPieceType:
            Converts a string representation of a chess piece
                (e.g., "p", "knight")
            to its corresponding ChessPieceType.
            Raises ValueError if the string does not correspond to a valid piece type.

        as_chess() -> chess.PieceType:
            Returns the corresponding `chess.PieceType` value for the ChessPieceType instance.
    """

    PAWN = "pawn"
    KNIGHT = "knight"
    BISHOP = "bishop"
    ROOK = "rook"
    QUEEN = "queen"
    KING = "king"

    @classmethod
    def from_str(cls, string: str) -> ChessPieceType:
        """Convert a string into a ChessPieceType."""
        mapping = {
            "p": cls.PAWN,
            "n": cls.KNIGHT,
            "b": cls.BISHOP,
            "r": cls.ROOK,
            "q": cls.QUEEN,
            "k": cls.KING,
            "pawn": cls.PAWN,
            "knight": cls.KNIGHT,
            "bishop": cls.BISHOP,
            "rook": cls.ROOK,
            "queen": cls.QUEEN,
            "king": cls.KING,
        }
        resolved = mapping.get(string.lower())
        if resolved is None:
            raise ValueError(f"Invalid piece string: {string}")
        return resolved

    def as_chess(self) -> chess.PieceType:
        """Return the python-chess piece type for this value."""
        mapping = {
            ChessPieceType.PAWN: chess.PAWN,
            ChessPieceType.KNIGHT: chess.KNIGHT,
            ChessPieceType.BISHOP: chess.BISHOP,
            ChessPieceType.ROOK: chess.ROOK,
            ChessPieceType.QUEEN: chess.QUEEN,
            ChessPieceType.KING: chess.KING,
        }
        return mapping[self]


_VULTURE_USED = (ChessPieceType.as_chess,)
