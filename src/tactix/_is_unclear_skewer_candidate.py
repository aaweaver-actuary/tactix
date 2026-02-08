"""Identify skewer candidates for unclear outcomes."""


def _is_unclear_skewer_candidate(
    motif: str,
    best_move: str,
    user_move_uci: str,
    result: str,
) -> bool:
    """Return True when the skewer outcome is unclear."""
    if motif != "skewer":
        return False
    if user_move_uci == best_move:
        return False
    return result in {"missed", "failed_attempt", "unclear"}
