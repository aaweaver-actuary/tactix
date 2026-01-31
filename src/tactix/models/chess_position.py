import chess
from pydantic import BaseModel


class ChessPosition(BaseModel):
    """Model representing a chess position in FEN notation."""

    fen: str
    turn: chess.Color
