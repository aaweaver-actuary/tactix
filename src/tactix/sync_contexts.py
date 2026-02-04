"""Shared dataclass containers for daily sync contexts."""

from __future__ import annotations

from dataclasses import dataclass

from tactix.chess_clients.base_chess_client import BaseChessClient
from tactix.config import Settings
from tactix.pipeline_state__pipeline import FetchContext, GameRow, ProgressCallback


@dataclass(frozen=True)
class DailySyncStartContext:
    """Inputs for emitting daily sync start events."""

    settings: Settings
    progress: ProgressCallback | None
    profile: str | None
    backfill_mode: bool
    window_start_ms: int | None
    window_end_ms: int | None


@dataclass(frozen=True)
class DailyGameSyncContext:
    """Inputs for running a daily game sync."""

    settings: Settings
    client: BaseChessClient
    progress: ProgressCallback | None
    window_start_ms: int | None
    window_end_ms: int | None
    profile: str | None


@dataclass(frozen=True)
class DailyGameSyncRequest:
    """Optional inputs for daily game sync requests."""

    settings: Settings | None = None
    source: str | None = None
    progress: ProgressCallback | None = None
    window_start_ms: int | None = None
    window_end_ms: int | None = None
    profile: str | None = None
    client: BaseChessClient | None = None


@dataclass(frozen=True)
class PrepareGamesForSyncContext:
    """Inputs for preparing games for sync."""

    settings: Settings
    client: BaseChessClient
    backfill_mode: bool
    window_start_ms: int | None
    window_end_ms: int | None
    progress: ProgressCallback | None


@dataclass(frozen=True)
class WindowFilterContext:
    """Inputs for reporting filtered window counts."""

    settings: Settings
    progress: ProgressCallback | None
    backfill_mode: bool
    window_filtered: int
    window_start_ms: int | None
    window_end_ms: int | None


@dataclass(frozen=True)
class FetchProgressContext:
    """Inputs for fetch progress updates."""

    settings: Settings
    progress: ProgressCallback | None
    fetch_context: FetchContext
    backfill_mode: bool
    window_start_ms: int | None
    window_end_ms: int | None
    fetched_games: int


@dataclass(frozen=True)
class DailySyncTotals:
    """Aggregated totals produced by a sync run."""

    raw_pgns_inserted: int
    postgres_raw_pgns_inserted: int
    positions_count: int
    tactics_count: int
    postgres_written: int
    postgres_synced: int
    metrics_version: int


@dataclass(frozen=True)
class DailySyncCompleteContext:
    """Context describing a completed daily sync run."""

    settings: Settings
    profile: str | None
    games: list[GameRow]
    totals: DailySyncTotals
    backfill_mode: bool

    @property
    def raw_pgns_inserted(self) -> int:
        """Return inserted raw PGN count."""
        return self.totals.raw_pgns_inserted

    @property
    def postgres_raw_pgns_inserted(self) -> int:
        """Return inserted Postgres raw PGN count."""
        return self.totals.postgres_raw_pgns_inserted

    @property
    def positions_count(self) -> int:
        """Return analyzed position count."""
        return self.totals.positions_count

    @property
    def tactics_count(self) -> int:
        """Return detected tactic count."""
        return self.totals.tactics_count

    @property
    def postgres_written(self) -> int:
        """Return Postgres tactics written count."""
        return self.totals.postgres_written

    @property
    def postgres_synced(self) -> int:
        """Return Postgres tactics synced count."""
        return self.totals.postgres_synced

    @property
    def metrics_version(self) -> int:
        """Return the metrics version."""
        return self.totals.metrics_version


@dataclass(frozen=True)
class RawPgnMetrics:
    """Metrics for raw PGN ingestion."""

    raw_pgns_inserted: int
    raw_pgns_hashed: int
    raw_pgns_matched: int
    postgres_raw_pgns_inserted: int


@dataclass(frozen=True)
class AnalysisMetrics:
    """Metrics for analysis output."""

    positions_count: int
    tactics_count: int
    metrics_version: int


@dataclass(frozen=True)
class DailySyncCheckpoint:
    """Checkpoint metadata for a sync run."""

    checkpoint_value: int | None
    last_timestamp_value: int


@dataclass(frozen=True)
class DailySyncPayloadMetrics:
    """Grouped metrics for daily sync payloads."""

    raw_pgns: RawPgnMetrics
    analysis: AnalysisMetrics
    checkpoint: DailySyncCheckpoint

    @property
    def raw_pgns_inserted(self) -> int:
        """Return inserted raw PGN count."""
        return self.raw_pgns.raw_pgns_inserted

    @property
    def raw_pgns_hashed(self) -> int:
        """Return hashed raw PGN count."""
        return self.raw_pgns.raw_pgns_hashed

    @property
    def raw_pgns_matched(self) -> int:
        """Return matched raw PGN count."""
        return self.raw_pgns.raw_pgns_matched

    @property
    def postgres_raw_pgns_inserted(self) -> int:
        """Return inserted Postgres raw PGN count."""
        return self.raw_pgns.postgres_raw_pgns_inserted

    @property
    def positions_count(self) -> int:
        """Return analyzed position count."""
        return self.analysis.positions_count

    @property
    def tactics_count(self) -> int:
        """Return detected tactic count."""
        return self.analysis.tactics_count

    @property
    def metrics_version(self) -> int:
        """Return the metrics version."""
        return self.analysis.metrics_version

    @property
    def checkpoint_value(self) -> int | None:
        """Return the checkpoint value."""
        return self.checkpoint.checkpoint_value

    @property
    def last_timestamp_value(self) -> int:
        """Return the last timestamp value."""
        return self.checkpoint.last_timestamp_value


@dataclass(frozen=True)
class DailySyncPayloadContext:
    """Context describing the daily sync payload."""

    settings: Settings
    fetch_context: FetchContext
    games: list[GameRow]
    metrics: DailySyncPayloadMetrics
    backfill_mode: bool

    @property
    def raw_pgns_inserted(self) -> int:
        """Return inserted raw PGN count."""
        return self.metrics.raw_pgns_inserted

    @property
    def raw_pgns_hashed(self) -> int:
        """Return hashed raw PGN count."""
        return self.metrics.raw_pgns_hashed

    @property
    def raw_pgns_matched(self) -> int:
        """Return matched raw PGN count."""
        return self.metrics.raw_pgns_matched

    @property
    def postgres_raw_pgns_inserted(self) -> int:
        """Return inserted Postgres raw PGN count."""
        return self.metrics.postgres_raw_pgns_inserted

    @property
    def positions_count(self) -> int:
        """Return analyzed position count."""
        return self.metrics.positions_count

    @property
    def tactics_count(self) -> int:
        """Return detected tactic count."""
        return self.metrics.tactics_count

    @property
    def metrics_version(self) -> int:
        """Return the metrics version."""
        return self.metrics.metrics_version

    @property
    def checkpoint_value(self) -> int | None:
        """Return the checkpoint value."""
        return self.metrics.checkpoint_value

    @property
    def last_timestamp_value(self) -> int:
        """Return the last timestamp value."""
        return self.metrics.last_timestamp_value


@dataclass(frozen=True)
class NoGamesWindowContext:
    """Grouped window metadata for no-games contexts."""

    fetch_context: FetchContext
    last_timestamp_value: int
    window_filtered: int


@dataclass(frozen=True)
class NoGamesPayloadContext:
    """Payload context when no games are returned."""

    settings: Settings
    conn: object
    backfill_mode: bool
    window: NoGamesWindowContext

    @property
    def fetch_context(self) -> FetchContext:
        """Return the fetch context."""
        return self.window.fetch_context

    @property
    def last_timestamp_value(self) -> int:
        """Return the last timestamp value."""
        return self.window.last_timestamp_value

    @property
    def window_filtered(self) -> int:
        """Return the filtered window count."""
        return self.window.window_filtered


@dataclass(frozen=True)
class NoGamesAfterDedupePayloadContext:
    """Payload context when games vanish after de-dupe."""

    settings: Settings
    conn: object
    backfill_mode: bool
    games: list[GameRow]
    window: NoGamesWindowContext

    @property
    def fetch_context(self) -> FetchContext:
        """Return the fetch context."""
        return self.window.fetch_context

    @property
    def last_timestamp_value(self) -> int:
        """Return the last timestamp value."""
        return self.window.last_timestamp_value

    @property
    def window_filtered(self) -> int:
        """Return the filtered window count."""
        return self.window.window_filtered


@dataclass(frozen=True)
class NoGamesContext:
    """Context for no-games handling."""

    settings: Settings
    conn: object
    progress: ProgressCallback | None
    backfill_mode: bool
    window: NoGamesWindowContext

    @property
    def fetch_context(self) -> FetchContext:
        """Return the fetch context."""
        return self.window.fetch_context

    @property
    def last_timestamp_value(self) -> int:
        """Return the last timestamp value."""
        return self.window.last_timestamp_value

    @property
    def window_filtered(self) -> int:
        """Return the filtered window count."""
        return self.window.window_filtered


@dataclass(frozen=True)
class NoGamesAfterDedupeContext:
    """Context for handling no-games after de-dupe."""

    settings: Settings
    conn: object
    progress: ProgressCallback | None
    backfill_mode: bool
    games: list[GameRow]
    window: NoGamesWindowContext

    @property
    def fetch_context(self) -> FetchContext:
        """Return the fetch context."""
        return self.window.fetch_context

    @property
    def last_timestamp_value(self) -> int:
        """Return the last timestamp value."""
        return self.window.last_timestamp_value

    @property
    def window_filtered(self) -> int:
        """Return the filtered window count."""
        return self.window.window_filtered
