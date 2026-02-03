from tactix._is_swing_at_least import _is_swing_at_least
from tactix._is_unclear_skewer_candidate import _is_unclear_skewer_candidate


def _should_mark_unclear_skewer(
    result: str,
    motif: str,
    best_move: str | None,
    user_move_uci: str,
    swing: int | None,
    threshold: int | None,
) -> bool:
    if swing is None or threshold is None or best_move is None:
        return False
    if not _is_unclear_skewer_candidate(motif, best_move, user_move_uci, result):
        return False
    return _is_swing_at_least(swing, threshold)
