def _resolve_user_rating(
    user: str,
    white: str | None,
    black: str | None,
    white_elo: int | None,
    black_elo: int | None,
) -> int | None:
    user_lower = user.lower()
    white_lower = (white or "").lower()
    black_lower = (black or "").lower()
    if white_lower == user_lower:
        return white_elo
    if black_lower == user_lower:
        return black_elo
    return None
