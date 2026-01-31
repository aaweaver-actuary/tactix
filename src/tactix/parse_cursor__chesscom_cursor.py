from __future__ import annotations


def _parse_cursor(cursor: str | None) -> tuple[int, str]:
    """Parse a cursor token into timestamp and id.

    Args:
        cursor: Cursor token.

    Returns:
        Tuple of timestamp and game id.
    """

    if not cursor:
        return 0, ""
    if ":" in cursor:
        prefix, suffix = cursor.split(":", 1)
        try:
            return int(prefix), suffix
        except ValueError:
            return 0, cursor
    if cursor.isdigit():
        return int(cursor), ""
    return 0, cursor
