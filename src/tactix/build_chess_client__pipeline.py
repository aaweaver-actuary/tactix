"""Build chess client instances for pipeline use."""

from __future__ import annotations

from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import logger
from tactix.infra.clients.chesscom_client import ChesscomClient, ChesscomClientContext
from tactix.infra.clients.lichess_client import LichessClient, LichessClientContext
from tactix.ports.game_source_client import GameSourceClient


def _build_chess_client(
    settings: Settings,
    client: GameSourceClient | None,
) -> GameSourceClient:
    """Return an existing client or build one based on settings."""
    if client is not None:
        return client
    if settings.source == "chesscom":
        return ChesscomClient(ChesscomClientContext(settings=settings, logger=logger))
    return LichessClient(LichessClientContext(settings=settings, logger=logger))
