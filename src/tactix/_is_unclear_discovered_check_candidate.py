"""Identify discovered check candidates for unclear outcomes."""


def _is_unclear_discovered_check_candidate(
    motif: str,
    best_move: str,
    user_move_uci: str,
    result: str,
) -> bool:
    if motif != "discovered_check":
        return False
    if user_move_uci == best_move:
        return False
    return result in {"missed", "unclear"}
