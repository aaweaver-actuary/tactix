"""Resolve which rating belongs to the user."""

from tactix._normalize_player_name import _normalize_player_name


def _resolve_user_rating(
    user: str,
    white: str | None,
    black: str | None,
    white_elo: int | None,
    black_elo: int | None,
) -> int | None:
    """Return the user's rating when present in the headers."""
    user_lower = _normalize_player_name(user)
    white_lower = _normalize_player_name(white)
    black_lower = _normalize_player_name(black)
    if white_lower == user_lower:
        return white_elo
    if black_lower == user_lower:
        return black_elo
    return None
