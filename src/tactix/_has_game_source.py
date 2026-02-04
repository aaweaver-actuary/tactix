"""Check if a game row includes a source value."""


def _has_game_source(game_id: str, source: str) -> bool:
    return bool(game_id and source)
