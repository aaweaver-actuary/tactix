from __future__ import annotations

from tactix import chesscom_client as _legacy
from tactix.chess_clients.base_chess_client import (
    ChessFetchRequest as ChesscomFetchRequest,
)
from tactix.chess_clients.base_chess_client import (
    ChessFetchResult as ChesscomFetchResult,
)
from tactix.chesscom_client import *  # noqa: F403
from tactix.errors import RateLimitError

try:
    ChesscomRateLimitError = _legacy.ChesscomRateLimitError
except AttributeError:  # pragma: no cover - legacy alias fallback
    ChesscomRateLimitError = RateLimitError

__all__ = list(_legacy.__all__)
__all__.append("ChesscomRateLimitError")
__all__.extend([ChesscomFetchRequest.__name__, ChesscomFetchResult.__name__])
