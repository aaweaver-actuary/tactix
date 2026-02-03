from tactix._is_swing_at_least import _is_swing_at_least
from tactix.analyze_tactics__positions import _MATE_IN_TWO_UNCLEAR_SWING_THRESHOLD, MATE_IN_TWO


def _should_mark_unclear_mate_in_two(
    result: str,
    best_move: str | None,
    user_move_uci: str,
    swing: int | None,
    mate_in: int | None,
) -> bool:
    return all(
        (
            mate_in == MATE_IN_TWO,
            best_move is not None,
            user_move_uci != best_move,
            result in {"missed", "failed_attempt", "unclear"},
            _is_swing_at_least(swing, _MATE_IN_TWO_UNCLEAR_SWING_THRESHOLD),
        )
    )
