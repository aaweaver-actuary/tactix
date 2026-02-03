from tactix._fallback_kwargs import _fallback_kwargs
from tactix.extract_positions_with_fallback__pgn import _extract_positions_with_fallback


def extract_positions(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> list[dict[str, object]]:
    return _extract_positions_with_fallback(
        pgn=pgn,
        user=user,
        source=source,
        game_id=game_id,
        side_to_move_filter=side_to_move_filter,
        **_fallback_kwargs(),
    )
