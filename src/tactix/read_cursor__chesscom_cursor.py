"""Read chess.com cursor tokens from disk."""

from __future__ import annotations

from pathlib import Path

from tactix.read_optional_text__filesystem import _read_optional_text


def read_cursor(path: Path) -> str | None:
    """Read a cursor token from disk.

    Args:
        path: Cursor path.

    Returns:
        Cursor token or None.
    """

    return _read_optional_text(path)
