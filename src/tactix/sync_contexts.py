"""Shared dataclass containers for daily sync contexts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from tactix.config import Settings
from tactix.FetchContext import FetchContext
from tactix.GameRow import GameRow
from tactix.pipeline_state__pipeline import ProgressCallback
from tactix.ports.game_source_client import GameSourceClient


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
    client: GameSourceClient
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
    client: GameSourceClient | None = None


@dataclass(frozen=True)
class PrepareGamesForSyncContext:
    """Inputs for preparing games for sync."""

    settings: Settings
    client: GameSourceClient
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


def _validate_allowed_kwargs(kwargs: dict[str, object], allowed_keys: set[str]) -> None:
    unknown = sorted(set(kwargs) - allowed_keys)
    if unknown:
        raise TypeError(f"Unexpected keyword arguments: {', '.join(unknown)}")


def _resolve_required_kwargs(
    kwargs: dict[str, object],
    required_keys: set[str],
) -> dict[str, object]:
    required_fields = {key: kwargs.get(key) for key in required_keys}
    missing = [name for name, value in required_fields.items() if value is None]
    if missing:
        raise TypeError(f"Missing required arguments: {', '.join(sorted(missing))}")
    return required_fields


def _collect_unexpected_kwargs(kwargs: dict[str, object], keys: set[str]) -> list[str]:
    return [name for name in keys if kwargs.get(name) is not None]


_NO_GAMES_WINDOW_KEYS = {"fetch_context", "last_timestamp_value", "window_filtered"}
_NO_GAMES_WINDOW_GAMES_KEYS = _NO_GAMES_WINDOW_KEYS | {"games"}


def _resolve_daily_sync_totals(
    totals: DailySyncTotals | None,
    totals_kwargs: dict[str, object],
) -> DailySyncTotals:
    allowed_keys = {
        "raw_pgns_inserted",
        "postgres_raw_pgns_inserted",
        "positions_count",
        "tactics_count",
        "postgres_written",
        "postgres_synced",
        "metrics_version",
    }
    _validate_allowed_kwargs(totals_kwargs, allowed_keys)
    if totals is None:
        required_fields = _resolve_required_kwargs(totals_kwargs, allowed_keys)
        return DailySyncTotals(
            raw_pgns_inserted=required_fields["raw_pgns_inserted"],
            postgres_raw_pgns_inserted=required_fields["postgres_raw_pgns_inserted"],
            positions_count=required_fields["positions_count"],
            tactics_count=required_fields["tactics_count"],
            postgres_written=required_fields["postgres_written"],
            postgres_synced=required_fields["postgres_synced"],
            metrics_version=required_fields["metrics_version"],
        )
    unexpected = _collect_unexpected_kwargs(totals_kwargs, allowed_keys)
    if unexpected:
        raise TypeError(f"Unexpected keyword arguments: {', '.join(sorted(unexpected))}")
    return totals


@dataclass(frozen=True, init=False)
class DailySyncCompleteContext:
    """Context describing a completed daily sync run."""

    settings: Settings
    profile: str | None
    games: list[GameRow]
    totals: DailySyncTotals
    backfill_mode: bool

    def __init__(
        self,
        settings: Settings,
        profile: str | None,
        games: list[GameRow],
        totals: DailySyncTotals | None = None,
        **totals_kwargs: object,
    ) -> None:
        backfill_mode = bool(totals_kwargs.pop("backfill_mode", False))
        totals = _resolve_daily_sync_totals(
            totals,
            totals_kwargs,
        )
        object.__setattr__(self, "settings", settings)
        object.__setattr__(self, "profile", profile)
        object.__setattr__(self, "games", games)
        object.__setattr__(self, "totals", totals)
        object.__setattr__(self, "backfill_mode", backfill_mode)

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


def _resolve_daily_sync_payload_metrics(
    metrics: DailySyncPayloadMetrics | None,
    metrics_kwargs: dict[str, object],
) -> DailySyncPayloadMetrics:
    allowed_keys = {
        "raw_pgns_inserted",
        "raw_pgns_hashed",
        "raw_pgns_matched",
        "postgres_raw_pgns_inserted",
        "positions_count",
        "tactics_count",
        "metrics_version",
        "checkpoint_value",
        "last_timestamp_value",
    }
    _validate_allowed_kwargs(metrics_kwargs, allowed_keys)
    if metrics is None:
        required_fields = _resolve_required_kwargs(
            metrics_kwargs,
            {
                "raw_pgns_inserted",
                "raw_pgns_hashed",
                "raw_pgns_matched",
                "postgres_raw_pgns_inserted",
                "positions_count",
                "tactics_count",
                "metrics_version",
                "last_timestamp_value",
            },
        )
        return DailySyncPayloadMetrics(
            raw_pgns=RawPgnMetrics(
                raw_pgns_inserted=required_fields["raw_pgns_inserted"],
                raw_pgns_hashed=required_fields["raw_pgns_hashed"],
                raw_pgns_matched=required_fields["raw_pgns_matched"],
                postgres_raw_pgns_inserted=required_fields["postgres_raw_pgns_inserted"],
            ),
            analysis=AnalysisMetrics(
                positions_count=required_fields["positions_count"],
                tactics_count=required_fields["tactics_count"],
                metrics_version=required_fields["metrics_version"],
            ),
            checkpoint=DailySyncCheckpoint(
                checkpoint_value=metrics_kwargs.get("checkpoint_value"),
                last_timestamp_value=required_fields["last_timestamp_value"],
            ),
        )
    unexpected = _collect_unexpected_kwargs(metrics_kwargs, allowed_keys)
    if unexpected:
        raise TypeError(f"Unexpected keyword arguments: {', '.join(sorted(unexpected))}")
    return metrics


@dataclass(frozen=True, init=False)
class DailySyncPayloadContext:
    """Context describing the daily sync payload."""

    settings: Settings
    fetch_context: FetchContext
    games: list[GameRow]
    metrics: DailySyncPayloadMetrics
    backfill_mode: bool

    def __init__(
        self,
        settings: Settings,
        fetch_context: FetchContext,
        games: list[GameRow],
        metrics: DailySyncPayloadMetrics | None = None,
        **metrics_kwargs: object,
    ) -> None:
        backfill_mode = bool(metrics_kwargs.pop("backfill_mode", False))
        metrics = _resolve_daily_sync_payload_metrics(
            metrics,
            metrics_kwargs,
        )
        object.__setattr__(self, "settings", settings)
        object.__setattr__(self, "fetch_context", fetch_context)
        object.__setattr__(self, "games", games)
        object.__setattr__(self, "metrics", metrics)
        object.__setattr__(self, "backfill_mode", backfill_mode)

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


def _resolve_no_games_window_context(
    window: NoGamesWindowContext | None,
    *,
    fetch_context: FetchContext | None,
    last_timestamp_value: int | None,
    window_filtered: int | None,
) -> NoGamesWindowContext:
    if window is None:
        _resolve_required_kwargs(
            {
                "fetch_context": fetch_context,
                "last_timestamp_value": last_timestamp_value,
                "window_filtered": window_filtered,
            },
            _NO_GAMES_WINDOW_KEYS,
        )
        return NoGamesWindowContext(
            fetch_context=fetch_context,
            last_timestamp_value=last_timestamp_value,
            window_filtered=window_filtered,
        )
    unexpected = _collect_unexpected_kwargs(
        {
            "fetch_context": fetch_context,
            "last_timestamp_value": last_timestamp_value,
            "window_filtered": window_filtered,
        },
        _NO_GAMES_WINDOW_KEYS,
    )
    if unexpected:
        raise TypeError(f"Unexpected keyword arguments: {', '.join(sorted(unexpected))}")
    return window


def _resolve_no_games_window_from_kwargs(
    window: NoGamesWindowContext | None,
    window_kwargs: dict[str, object],
    *,
    allowed_keys: set[str],
) -> NoGamesWindowContext:
    _validate_allowed_kwargs(window_kwargs, allowed_keys)
    return _resolve_no_games_window_context(
        window,
        fetch_context=window_kwargs.get("fetch_context"),
        last_timestamp_value=window_kwargs.get("last_timestamp_value"),
        window_filtered=window_kwargs.get("window_filtered"),
    )


def _require_no_games_payload_games(window_kwargs: dict[str, object]) -> list[GameRow]:
    games = window_kwargs.get("games")
    if games is None:
        raise TypeError("Missing required arguments: games")
    return cast(list[GameRow], games)


class _NoGamesWindowAccessors:
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


@dataclass(frozen=True, init=False)
class NoGamesPayloadContext(_NoGamesWindowAccessors):
    """Payload context when no games are returned."""

    settings: Settings
    conn: object
    backfill_mode: bool
    window: NoGamesWindowContext

    def __init__(
        self,
        settings: Settings,
        conn: object,
        backfill_mode: bool,
        window: NoGamesWindowContext | None = None,
        **window_kwargs: object,
    ) -> None:
        window = _resolve_no_games_window_from_kwargs(
            window,
            window_kwargs,
            allowed_keys=_NO_GAMES_WINDOW_KEYS,
        )
        object.__setattr__(self, "settings", settings)
        object.__setattr__(self, "conn", conn)
        object.__setattr__(self, "backfill_mode", backfill_mode)
        object.__setattr__(self, "window", window)


@dataclass(frozen=True, init=False)
class NoGamesAfterDedupePayloadContext(_NoGamesWindowAccessors):
    """Payload context when games vanish after de-dupe."""

    settings: Settings
    conn: object
    backfill_mode: bool
    games: list[GameRow]
    window: NoGamesWindowContext

    def __init__(
        self,
        settings: Settings,
        conn: object,
        backfill_mode: bool,
        window: NoGamesWindowContext | None = None,
        **window_kwargs: object,
    ) -> None:
        games = _require_no_games_payload_games(window_kwargs)
        window = _resolve_no_games_window_from_kwargs(
            window,
            window_kwargs,
            allowed_keys=_NO_GAMES_WINDOW_GAMES_KEYS,
        )
        object.__setattr__(self, "settings", settings)
        object.__setattr__(self, "conn", conn)
        object.__setattr__(self, "backfill_mode", backfill_mode)
        object.__setattr__(self, "games", games)
        object.__setattr__(self, "window", window)


@dataclass(frozen=True, init=False)
class NoGamesContext(_NoGamesWindowAccessors):
    """Context for no-games handling."""

    settings: Settings
    conn: object
    progress: ProgressCallback | None
    backfill_mode: bool
    window: NoGamesWindowContext

    def __init__(
        self,
        settings: Settings,
        conn: object,
        progress: ProgressCallback | None,
        window: NoGamesWindowContext | None = None,
        **window_kwargs: object,
    ) -> None:
        backfill_mode = bool(window_kwargs.pop("backfill_mode", False))
        window = _resolve_no_games_window_from_kwargs(
            window,
            window_kwargs,
            allowed_keys=_NO_GAMES_WINDOW_KEYS,
        )
        object.__setattr__(self, "settings", settings)
        object.__setattr__(self, "conn", conn)
        object.__setattr__(self, "progress", progress)
        object.__setattr__(self, "backfill_mode", backfill_mode)
        object.__setattr__(self, "window", window)


@dataclass(frozen=True, init=False)
class NoGamesAfterDedupeContext(_NoGamesWindowAccessors):
    """Context for handling no-games after de-dupe."""

    settings: Settings
    conn: object
    progress: ProgressCallback | None
    backfill_mode: bool
    games: list[GameRow]
    window: NoGamesWindowContext

    def __init__(
        self,
        settings: Settings,
        conn: object,
        progress: ProgressCallback | None,
        window: NoGamesWindowContext | None = None,
        **window_kwargs: object,
    ) -> None:
        backfill_mode = bool(window_kwargs.pop("backfill_mode", False))
        games = _require_no_games_payload_games(window_kwargs)
        window = _resolve_no_games_window_from_kwargs(
            window,
            window_kwargs,
            allowed_keys=_NO_GAMES_WINDOW_GAMES_KEYS,
        )
        object.__setattr__(self, "settings", settings)
        object.__setattr__(self, "conn", conn)
        object.__setattr__(self, "progress", progress)
        object.__setattr__(self, "backfill_mode", backfill_mode)
        object.__setattr__(self, "games", games)
        object.__setattr__(self, "window", window)
