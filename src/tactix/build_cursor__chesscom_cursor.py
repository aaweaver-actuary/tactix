from __future__ import annotations


def _build_cursor(last_ts: int, game_id: str) -> str:
    """Build a cursor token.

    Args:
        last_ts: Last timestamp in milliseconds.
        game_id: Game identifier.

    Returns:
        Cursor token.
    """

    return f"{last_ts}:{game_id}"
