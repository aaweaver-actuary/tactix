from __future__ import annotations

from collections.abc import Callable

from tactix.normalize_pgn_text__db_store import _normalize_pgn_text
from tactix.utils import hash


def _resolve_pgn_hash(
    pgn_text: str,
    normalize_pgn: Callable[[str], str] | None,
    hash_pgn: Callable[[str], str] | None,
) -> tuple[str | None, str]:
    normalized = _normalize_pgn_text(pgn_text, normalize_pgn)
    hasher = hash_pgn if hash_pgn is not None else hash
    source = normalized if normalized is not None else pgn_text
    return normalized, hasher(source)
