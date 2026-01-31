from __future__ import annotations

from dataclasses import dataclass

from tactix.chess_clients.base_chess_client import BaseChessClientContext


@dataclass(slots=True)
class ChesscomClientContext(BaseChessClientContext):
    """Context for Chess.com API interactions."""
