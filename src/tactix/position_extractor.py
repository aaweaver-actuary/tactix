from __future__ import annotations

import chess

from tactix import extract_positions__pgn as _impl
from tactix._build_pgn_context import _build_pgn_context
from tactix._clock_from_comment import _clock_from_comment
from tactix._iter_position_contexts import _iter_position_contexts
from tactix._normalize_side_filter import _normalize_side_filter
from tactix._resolve_game_context import _resolve_game_context
from tactix.PgnContext import PgnContext

__all__ = [name for name in dir(_impl) if not name.startswith("__")]
globals().update({name: getattr(_impl, name) for name in __all__})

_EXTRA_EXPORTS = {
    "PgnContext": PgnContext,
    "_build_pgn_context": _build_pgn_context,
    "_clock_from_comment": _clock_from_comment,
    "_iter_position_contexts": _iter_position_contexts,
    "_normalize_side_filter": _normalize_side_filter,
    "_resolve_game_context": _resolve_game_context,
    "chess": chess,
}
globals().update(_EXTRA_EXPORTS)
__all__ += list(_EXTRA_EXPORTS)

_extract_positions_python = _impl._extract_positions_python
_load_rust_extractor = _impl._load_rust_extractor
_call_rust_extractor = _impl._call_rust_extractor
