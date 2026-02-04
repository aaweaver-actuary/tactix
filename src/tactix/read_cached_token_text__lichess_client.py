"""Read raw cached token text from disk."""

from __future__ import annotations

from pathlib import Path

from tactix.read_optional_text__filesystem import _read_optional_text


def _read_cached_token_text(path: Path) -> str | None:
    """Return cached token text if present."""
    return _read_optional_text(path)
