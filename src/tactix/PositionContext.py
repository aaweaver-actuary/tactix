"""Context for a single chess position."""

# pylint: disable=invalid-name

from dataclasses import dataclass


@dataclass
class PositionContext:  # pylint: disable=too-many-instance-attributes
    """Structured position data extracted from a game."""

    game_id: str
    user: str
    source: str
    fen: str
    ply: int
    move_number: int
    side_to_move: str
    user_to_move: bool
    uci: str
    san: str
    clock_seconds: float | None
    is_legal: bool
