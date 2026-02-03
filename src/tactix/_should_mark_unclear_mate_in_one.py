from tactix.analyze_tactics__positions import _MATE_IN_ONE_UNCLEAR_SCORE_THRESHOLD, MATE_IN_ONE


def _should_mark_unclear_mate_in_one(
    result: str,
    best_move: str | None,
    user_move_uci: str,
    after_cp: int,
    mate_in: int | None,
) -> bool:
    return bool(
        mate_in == MATE_IN_ONE
        and best_move is not None
        and user_move_uci != best_move
        and result in {"missed", "failed_attempt"}
        and after_cp >= _MATE_IN_ONE_UNCLEAR_SCORE_THRESHOLD
    )
