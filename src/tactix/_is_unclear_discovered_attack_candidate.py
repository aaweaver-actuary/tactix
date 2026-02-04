"""Identify discovered attack candidates for unclear outcomes."""


def _is_unclear_discovered_attack_candidate(
    motif: str,
    best_move: str,
    user_move_uci: str,
    result: str,
) -> bool:
    if motif != "discovered_attack":
        return False
    if user_move_uci == best_move:
        return False
    return result in {"missed", "unclear"}
