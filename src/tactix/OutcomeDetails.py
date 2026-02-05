from dataclasses import dataclass


@dataclass(frozen=True)
class OutcomeDetails:
    result: str
    user_move_uci: str
    delta: int
