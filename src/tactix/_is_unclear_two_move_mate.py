from tactix.analyze_tactics__positions import _MATE_IN_TWO_UNCLEAR_SWING_THRESHOLD


def _is_unclear_two_move_mate(
    result: str,
    best_move: str | None,
    user_move_uci: str,
    swing: int | None,
) -> bool:
    if result != "unclear" or best_move is None:
        return False
    if user_move_uci == best_move:
        return False
    if swing is None:
        return False
    return swing <= _MATE_IN_TWO_UNCLEAR_SWING_THRESHOLD
