def _extract_positions_fallback(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None,
    side_to_move_filter: str | None,
) -> list[dict[str, object]]:
    from tactix import position_extractor  # noqa: PLC0415

    return position_extractor._extract_positions_python(
        pgn,
        user,
        source,
        game_id,
        side_to_move_filter=side_to_move_filter,
    )
