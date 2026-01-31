from __future__ import annotations

from pathlib import Path


def read_cursor(path: Path) -> str | None:
    """Read a cursor token from disk.

    Args:
        path: Cursor path.

    Returns:
        Cursor token or None.
    """

    try:
        raw = path.read_text().strip()
    except FileNotFoundError:
        return None
    return raw or None
