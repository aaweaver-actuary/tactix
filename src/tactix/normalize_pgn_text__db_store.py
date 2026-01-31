from __future__ import annotations

from collections.abc import Callable


def _normalize_pgn_text(
    pgn_text: str,
    normalize_pgn: Callable[[str], str] | None,
) -> str | None:
    return normalize_pgn(pgn_text) if normalize_pgn else None
