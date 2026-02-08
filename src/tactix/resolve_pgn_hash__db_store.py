"""Resolve PGN hash values for storage."""

from __future__ import annotations

from collections.abc import Callable

from tactix.normalize_pgn_text__db_store import _normalize_pgn_text
from tactix.utils import hash as hash_value


def _resolve_pgn_hash(
    pgn_text: str,
    normalize_pgn: Callable[[str], str] | None,
    hash_pgn: Callable[[str], str] | None,
) -> tuple[str | None, str]:
    """Return normalized PGN text and its hash."""
    normalized = _normalize_pgn_text(pgn_text, normalize_pgn)
    hasher = hash_pgn if hash_pgn is not None else hash_value
    source = normalized if normalized is not None else pgn_text
    return normalized, hasher(source)
