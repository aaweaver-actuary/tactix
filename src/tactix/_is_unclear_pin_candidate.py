"""Identify pin candidates for unclear outcomes."""


def _is_unclear_pin_candidate(
    motif: str,
    best_move: str,
    user_move_uci: str,
    result: str,
) -> bool:
    if motif != "pin":
        return False
    if user_move_uci == best_move:
        return False
    return result in {"missed", "unclear"}
