from __future__ import annotations

from pathlib import Path

from tactix.parse_cached_token__lichess_client import _parse_cached_token
from tactix.read_cached_token_text__lichess_client import _read_cached_token_text


def _read_cached_token(path: Path) -> str | None:
    """Read a cached OAuth token from disk.

    Args:
        path: Token cache path.

    Returns:
        Cached token string if available.
    """

    raw = _read_cached_token_text(path)
    if raw is None:
        return None
    return _parse_cached_token(raw)
