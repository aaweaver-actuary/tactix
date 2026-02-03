from tactix._should_mark_unclear_hanging_piece import _should_mark_unclear_hanging_piece


def _apply_outcome__unclear_hanging_piece(
    result: str,
    motif: str,
    best_move: str | None,
    user_move_uci: str,
    swing: int | None,
    threshold: int | None,
) -> str:
    if _should_mark_unclear_hanging_piece(
        result,
        motif,
        best_move,
        user_move_uci,
        swing,
        threshold,
    ):
        return "unclear"
    return result
