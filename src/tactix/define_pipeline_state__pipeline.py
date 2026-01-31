from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict

from tactix.chess_clients.chesscom_client import ChesscomFetchResult
from tactix.utils.logger import get_logger

logger = get_logger("tactix.pipeline")

ANALYSIS_PROGRESS_BUCKETS = 20
DEFAULT_SYNC_LIMIT = 50
INDEX_OFFSET = 1
RESUME_INDEX_START = 0
SINGLE_PGN_CHUNK = 1
ZERO_COUNT = 0
LICHESS_BLACK_PROFILES = {"bullet", "blitz", "rapid", "classical", "correspondence"}
CHESSCOM_BLACK_PROFILES = {
    "bullet",
    "blitz",
    "rapid",
    "classical",
    "correspondence",
    "daily",
}


class GameRow(TypedDict):
    game_id: str
    user: str
    source: str
    fetched_at: datetime
    pgn: str
    last_timestamp_ms: int


ProgressCallback = Callable[[dict[str, object]], None]


@dataclass(slots=True)
class FetchContext:
    raw_games: list[Mapping[str, object]]
    since_ms: int
    cursor_before: str | None = None
    cursor_value: str | None = None
    next_cursor: str | None = None
    chesscom_result: ChesscomFetchResult | None = None
    last_timestamp_ms: int = 0


@dataclass(slots=True)
class AnalysisPrepResult:
    positions: list[dict[str, object]]
    resume_index: int
    analysis_signature: str
    raw_pgns_inserted: int
    raw_pgns_hashed: int
    raw_pgns_matched: int
    postgres_raw_pgns_inserted: int


@dataclass(slots=True)
class DailyAnalysisResult:
    total_positions: int
    tactics_count: int
    postgres_written: int
    postgres_synced: int
    metrics_version: int
