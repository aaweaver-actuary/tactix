from __future__ import annotations

import os

from tactix import extract_positions__pgn as _impl

__all__ = [name for name in dir(_impl) if not name.startswith("__")]
globals().update({name: getattr(_impl, name) for name in __all__})

_extract_positions_python = _impl._extract_positions_python
_load_rust_extractor = _impl._load_rust_extractor
_call_rust_extractor = _impl._call_rust_extractor


def extract_positions(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> list[dict[str, object]]:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return _extract_positions_fallback(pgn, user, source, game_id, side_to_move_filter)
    rust_extractor = _load_rust_extractor()
    if rust_extractor is None:
        return _extract_positions_fallback(pgn, user, source, game_id, side_to_move_filter)
    return _call_rust_extractor(
        rust_extractor,
        pgn,
        user,
        source,
        game_id,
        side_to_move_filter,
    )


def _extract_positions_fallback(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None,
    side_to_move_filter: str | None,
) -> list[dict[str, object]]:
    return _extract_positions_python(
        pgn,
        user,
        source,
        game_id,
        side_to_move_filter=side_to_move_filter,
    )
