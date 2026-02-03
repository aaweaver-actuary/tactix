from tactix.PgnContext import PgnContext


def _build_pgn_context(
    pgn: str | PgnContext,
    user: str | None = None,
    source: str | None = None,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> PgnContext:
    if isinstance(pgn, PgnContext):
        return pgn
    if user is None or source is None:
        raise ValueError("user and source are required when pgn is a string")
    return PgnContext(
        pgn=pgn,
        user=user,
        source=source,
        game_id=game_id,
        side_to_move_filter=side_to_move_filter,
    )
