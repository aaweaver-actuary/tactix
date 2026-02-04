from datetime import datetime
from typing import TypedDict


class GameRow(TypedDict):
    """Typed dictionary for raw game rows."""

    game_id: str
    user: str
    source: str
    fetched_at: datetime
    pgn: str
    last_timestamp_ms: int
