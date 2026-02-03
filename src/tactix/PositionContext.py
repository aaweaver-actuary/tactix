from dataclasses import dataclass


@dataclass
class PositionContext:
    game_id: str
    user: str
    source: str
    fen: str
    ply: int
    move_number: int
    side_to_move: str
    uci: str
    san: str
    clock_seconds: float | None
    is_legal: bool
