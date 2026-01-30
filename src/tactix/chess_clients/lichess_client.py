from __future__ import annotations

from tactix import lichess_client as _legacy
from tactix.lichess_client import *  # noqa: F403

LichessTokenError = _legacy.LichessTokenError
_coerce_pgn_text = _legacy._coerce_pgn_text
_pgn_to_game_row = _legacy._pgn_to_game_row
_resolve_perf_value = _legacy._resolve_perf_value

__all__ = list(_legacy.__all__)
__all__.append("LichessTokenError")
__all__.append("_coerce_pgn_text")
__all__.append("_pgn_to_game_row")
__all__.append("_resolve_perf_value")
