from tactix._should_mark_unclear_pin import _should_mark_unclear_pin


def _apply_outcome__unclear_pin(
    result: str,
    motif: str,
    best_move: str | None,
    user_move_uci: str,
    swing: int | None,
    threshold: int | None,
) -> str:
    if _should_mark_unclear_pin(result, motif, best_move, user_move_uci, swing, threshold):
        return "unclear"
    return result
