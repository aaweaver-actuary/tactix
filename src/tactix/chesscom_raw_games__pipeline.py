from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from tactix.chess_clients.chesscom_client import ChesscomFetchResult


def _chesscom_raw_games(chesscom_result: ChesscomFetchResult) -> list[Mapping[str, object]]:
    return [cast(Mapping[str, object], row) for row in chesscom_result.games]
