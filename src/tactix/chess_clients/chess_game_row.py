from datetime import datetime

from pydantic import BaseModel


class ChessGameRow(BaseModel):
    """Represents a normalized chess game row.

    Attributes:
        game_id: Stable identifier for the game.
        user: Username associated with the game.
        source: Data source (e.g., "lichess" or "chesscom").
        fetched_at: Timestamp when the game was fetched.
        pgn: Raw PGN text.
        last_timestamp_ms: Last move timestamp in milliseconds.
    """

    game_id: str
    user: str
    source: str
    fetched_at: datetime
    pgn: str
    last_timestamp_ms: int
