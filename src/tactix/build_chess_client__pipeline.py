"""Build chess client instances for pipeline use."""

from __future__ import annotations

from tactix.chess_clients.base_chess_client import BaseChessClient
from tactix.chess_clients.chesscom_client import ChesscomClient, ChesscomClientContext
from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import logger
from tactix.lichess_client import LichessClient, LichessClientContext


def _build_chess_client(
    settings: Settings,
    client: BaseChessClient | None,
) -> BaseChessClient:
    """Return an existing client or build one based on settings."""
    if client is not None:
        return client
    if settings.source == "chesscom":
        return ChesscomClient(ChesscomClientContext(settings=settings, logger=logger))
    return LichessClient(LichessClientContext(settings=settings, logger=logger))
