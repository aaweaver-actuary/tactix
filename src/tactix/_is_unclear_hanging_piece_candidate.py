"""Identify unclear hanging piece outcomes."""


def _is_unclear_hanging_piece_candidate(
    motif: str,
    best_move: str,
    user_move_uci: str,
    result: str,
) -> bool:
    """Return True when the hanging piece outcome can be unclear."""
    if motif != "hanging_piece":
        return False
    if user_move_uci == best_move:
        return False
    return result in {"failed_attempt", "unclear"}
