from tactix._should_mark_unclear_discovered_attack import _should_mark_unclear_discovered_attack


def _apply_outcome__unclear_discovered_attack(
    result: str,
    motif: str,
    best_move: str | None,
    user_move_uci: str,
    swing: int | None,
    threshold: int | None,
) -> str:
    if _should_mark_unclear_discovered_attack(
        result,
        motif,
        best_move,
        user_move_uci,
        swing,
        threshold,
    ):
        return "unclear"
    return result
