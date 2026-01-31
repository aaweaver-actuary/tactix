from __future__ import annotations

from tactix.config import Settings
from tactix.define_chesscom_client__chesscom_client import ChesscomClient, logger
from tactix.define_chesscom_client_context__chesscom_client import ChesscomClientContext


def _client_for_settings(settings: Settings) -> ChesscomClient:
    context = ChesscomClientContext(settings=settings, logger=logger)
    return ChesscomClient(context)
