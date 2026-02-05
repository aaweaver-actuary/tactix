"""Public exports for chess client abstractions."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from tactix.chess_clients.base_chess_client import BaseChessClient, BaseChessClientContext
from tactix.chess_clients.chess_fetch_request import ChessFetchRequest
from tactix.chess_clients.chess_fetch_result import ChessFetchResult
from tactix.chess_clients.chess_game_row import ChessGameRow

__all__ = [
    "BaseChessClient",
    "BaseChessClientContext",
    "ChessFetchRequest",
    "ChessFetchResult",
    "ChessGameRow",
    "ChesscomClient",
    "LichessClient",
]


def __getattr__(name: str):
    if name == "ChesscomClient":
        return import_module("tactix.infra.clients.chesscom_client").ChesscomClient
    if name == "LichessClient":
        return import_module("tactix.infra.clients.lichess_client").LichessClient
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    return sorted(__all__)


if TYPE_CHECKING:
    from tactix.infra.clients.chesscom_client import ChesscomClient
    from tactix.infra.clients.lichess_client import LichessClient

    __getattr__("ChesscomClient")
    __getattr__("LichessClient")
    __dir__()
