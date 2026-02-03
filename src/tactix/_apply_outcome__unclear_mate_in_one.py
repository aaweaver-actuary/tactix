from tactix._should_mark_unclear_mate_in_one import _should_mark_unclear_mate_in_one


def _apply_outcome__unclear_mate_in_one(
    result: str,
    best_move: str | None,
    user_move_uci: str,
    after_cp: int,
    mate_in: int | None,
) -> str:
    if _should_mark_unclear_mate_in_one(
        result,
        best_move,
        user_move_uci,
        after_cp,
        mate_in,
    ):
        return "unclear"
    return result
