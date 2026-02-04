from dataclasses import dataclass

from tactix.chess_clients.base_chess_client import BaseChessClient
from tactix.config import Settings
from tactix.pipeline_state__pipeline import FetchContext, GameRow, ProgressCallback


@dataclass(frozen=True)
class DailySyncStartContext:
    settings: Settings
    progress: ProgressCallback | None
    profile: str | None
    backfill_mode: bool
    window_start_ms: int | None
    window_end_ms: int | None


@dataclass(frozen=True)
class DailyGameSyncContext:
    settings: Settings
    client: BaseChessClient
    progress: ProgressCallback | None
    window_start_ms: int | None
    window_end_ms: int | None
    profile: str | None


@dataclass(frozen=True)
class DailyGameSyncRequest:
    settings: Settings | None = None
    source: str | None = None
    progress: ProgressCallback | None = None
    window_start_ms: int | None = None
    window_end_ms: int | None = None
    profile: str | None = None
    client: BaseChessClient | None = None


@dataclass(frozen=True)
class PrepareGamesForSyncContext:
    settings: Settings
    client: BaseChessClient
    backfill_mode: bool
    window_start_ms: int | None
    window_end_ms: int | None
    progress: ProgressCallback | None


@dataclass(frozen=True)
class WindowFilterContext:
    settings: Settings
    progress: ProgressCallback | None
    backfill_mode: bool
    window_filtered: int
    window_start_ms: int | None
    window_end_ms: int | None


@dataclass(frozen=True)
class FetchProgressContext:
    settings: Settings
    progress: ProgressCallback | None
    fetch_context: FetchContext
    backfill_mode: bool
    window_start_ms: int | None
    window_end_ms: int | None
    fetched_games: int


@dataclass(frozen=True)
class DailySyncCompleteContext:
    settings: Settings
    profile: str | None
    games: list[GameRow]
    raw_pgns_inserted: int
    postgres_raw_pgns_inserted: int
    positions_count: int
    tactics_count: int
    postgres_written: int
    postgres_synced: int
    metrics_version: int
    backfill_mode: bool


@dataclass(frozen=True)
class DailySyncPayloadContext:
    settings: Settings
    fetch_context: FetchContext
    games: list[GameRow]
    raw_pgns_inserted: int
    raw_pgns_hashed: int
    raw_pgns_matched: int
    postgres_raw_pgns_inserted: int
    positions_count: int
    tactics_count: int
    metrics_version: int
    checkpoint_value: int | None
    last_timestamp_value: int
    backfill_mode: bool


@dataclass(frozen=True)
class NoGamesPayloadContext:
    settings: Settings
    conn: object
    backfill_mode: bool
    fetch_context: FetchContext
    last_timestamp_value: int
    window_filtered: int


@dataclass(frozen=True)
class NoGamesAfterDedupePayloadContext:
    settings: Settings
    conn: object
    backfill_mode: bool
    fetch_context: FetchContext
    last_timestamp_value: int
    games: list[GameRow]
    window_filtered: int


@dataclass(frozen=True)
class NoGamesContext:
    settings: Settings
    conn: object
    progress: ProgressCallback | None
    backfill_mode: bool
    fetch_context: FetchContext
    last_timestamp_value: int
    window_filtered: int


@dataclass(frozen=True)
class NoGamesAfterDedupeContext:
    settings: Settings
    conn: object
    progress: ProgressCallback | None
    backfill_mode: bool
    fetch_context: FetchContext
    last_timestamp_value: int
    games: list[GameRow]
    window_filtered: int
