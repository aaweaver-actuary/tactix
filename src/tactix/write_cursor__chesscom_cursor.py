"""Write chess.com cursor tokens to disk."""

from __future__ import annotations

from pathlib import Path


def write_cursor(path: Path, cursor: str | None) -> None:
    """Write a cursor token to disk.

    Args:
        path: Cursor file path.
        cursor: Cursor token to persist.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    if cursor is None:
        path.write_text("")
        return
    path.write_text(cursor)
