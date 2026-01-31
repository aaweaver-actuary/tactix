from __future__ import annotations

from tactix.cursor_allows_game__chesscom_cursor import _cursor_allows_game
from tactix.parse_cursor__chesscom_cursor import _parse_cursor


def _filter_by_cursor(rows: list[dict], cursor: str | None) -> list[dict]:
    """Filter rows using a cursor token.

    Args:
        rows: Candidate rows to filter.
        cursor: Cursor token to apply.

    Returns:
        Filtered list of rows.
    """

    since_ts, since_game = _parse_cursor(cursor)
    ordered = sorted(rows, key=lambda g: int(g.get("last_timestamp_ms", 0)))
    return [game for game in ordered if _cursor_allows_game(game, since_ts, since_game)]
