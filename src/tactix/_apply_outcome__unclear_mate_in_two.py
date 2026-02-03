from tactix._should_mark_unclear_mate_in_two import _should_mark_unclear_mate_in_two


def _apply_outcome__unclear_mate_in_two(
    result: str,
    best_move: str | None,
    user_move_uci: str,
    swing: int | None,
    mate_in: int | None,
) -> str:
    if _should_mark_unclear_mate_in_two(
        result,
        best_move,
        user_move_uci,
        swing,
        mate_in,
    ):
        return "unclear"
    return result
