from __future__ import annotations


def _cursor_allows_game(game: dict, since_ts: int, since_game: str) -> bool:
    last_ts = int(game.get("last_timestamp_ms", 0))
    return (
        (not since_ts)
        or (last_ts > since_ts)
        or (last_ts == since_ts and str(game.get("game_id", "")) > since_game)
    )
