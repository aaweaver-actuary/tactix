"""Extract raw game rows from Chess.com fetch results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from tactix.infra.clients.chesscom_client import ChesscomFetchResult


def _chesscom_raw_games(chesscom_result: ChesscomFetchResult) -> list[Mapping[str, object]]:
    """Return raw game row mappings from a fetch result."""
    return [cast(Mapping[str, object], row) for row in chesscom_result.games]
