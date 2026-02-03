from tactix._is_missed_mate import _is_missed_mate
from tactix._is_unclear_two_move_mate import _is_unclear_two_move_mate
from tactix.analyze_tactics__positions import (
    _MATE_MISSED_SCORE_MULTIPLIER,
    MATE_IN_ONE,
    MATE_IN_TWO,
)


def _should_upgrade_mate_result(
    result: str,
    best_move: str | None,
    user_move_uci: str,
    after_cp: int,
    swing: int | None,
    mate_in: int | None,
) -> bool:
    if mate_in not in {MATE_IN_ONE, MATE_IN_TWO}:
        return False
    missed_threshold = _MATE_MISSED_SCORE_MULTIPLIER * mate_in
    if _is_missed_mate(result, after_cp, missed_threshold):
        return True
    if mate_in == MATE_IN_TWO:
        return _is_unclear_two_move_mate(result, best_move, user_move_uci, swing)
    return False
