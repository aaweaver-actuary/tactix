from __future__ import annotations

import os
from collections.abc import Callable
from typing import TypedDict

from tactix import extract_positions__pgn as _impl
from tactix.extract_positions_with_fallback__pgn import _extract_positions_with_fallback

__all__ = [name for name in dir(_impl) if not name.startswith("__")]
globals().update({name: getattr(_impl, name) for name in __all__})

_extract_positions_python = _impl._extract_positions_python
_load_rust_extractor = _impl._load_rust_extractor
_call_rust_extractor = _impl._call_rust_extractor


class _FallbackKwargs(TypedDict):
    getenv: Callable[[str], str | None]
    load_rust_extractor: Callable[[], object | None]
    call_rust_extractor: Callable[
        [object, str, str, str, str | None, str | None],
        list[dict[str, object]],
    ]
    extract_positions_fallback: Callable[
        [str, str, str, str | None, str | None],
        list[dict[str, object]],
    ]


def extract_positions(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> list[dict[str, object]]:
    return _extract_positions_with_fallback(
        pgn=pgn,
        user=user,
        source=source,
        game_id=game_id,
        side_to_move_filter=side_to_move_filter,
        **_fallback_kwargs(),
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


def _fallback_kwargs() -> _FallbackKwargs:
    return {
        "getenv": os.getenv,
        "load_rust_extractor": _load_rust_extractor,
        "call_rust_extractor": _call_rust_extractor,
        "extract_positions_fallback": _extract_positions_fallback,
    }
