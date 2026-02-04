from collections.abc import Mapping
from dataclasses import dataclass

from tactix.chess_clients.chesscom_client import ChesscomFetchResult


@dataclass(slots=True)
class FetchContext:
    """Inputs describing fetched game batches."""

    raw_games: list[Mapping[str, object]]
    since_ms: int
    cursor_before: str | None = None
    cursor_value: str | None = None
    next_cursor: str | None = None
    chesscom_result: ChesscomFetchResult | None = None
    last_timestamp_ms: int = 0
