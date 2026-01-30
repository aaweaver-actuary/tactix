from __future__ import annotations

from tactix import chesscom_client as _legacy
from tactix.chesscom_client import *  # noqa: F403

ChesscomRateLimitError = _legacy.ChesscomRateLimitError

__all__ = list(_legacy.__all__)
__all__.append("ChesscomRateLimitError")
