"""Object-backed pipeline helpers consolidated from small pipeline modules."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass

from tactix.chess_clients.chesscom_client import write_cursor as write_chesscom_cursor
from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import (
    CHESSCOM_BLACK_PROFILES,
    INDEX_OFFSET,
    LICHESS_BLACK_PROFILES,
    ZERO_COUNT,
    ProgressCallback,
    logger,
)
from tactix.FetchContext import FetchContext
from tactix.GameRow import GameRow
from tactix.infra.clients.lichess_client import write_checkpoint
from tactix.latest_timestamp import latest_timestamp
from tactix.no_games_payload_contexts import (
    build_no_games_after_dedupe_payload_context,
    build_no_games_payload_context,
)
from tactix.ops_event import OpsEvent
from tactix.record_ops_event import record_ops_event
from tactix.sync_contexts import (
    DailySyncStartContext,
    FetchProgressContext,
    NoGamesAfterDedupeContext,
    NoGamesAfterDedupePayloadContext,
    NoGamesContext,
    NoGamesPayloadContext,
    WindowFilterContext,
)
from tactix.update_metrics_and_version__pipeline import _update_metrics_and_version
from tactix.utils.normalize_string import normalize_string


class PipelineCoercions:
    """Coerce pipeline input values into canonical types."""

    def coerce_int(self, value: object) -> int:
        """Return an integer representation of the value."""
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return 0
        return 0

    def coerce_str(self, value: object) -> str:
        """Return a string representation of the value."""
        if isinstance(value, str):
            return value
        if value is None:
            return ""
        return str(value)

    def coerce_pgn(self, value: object) -> str:
        """Return a string PGN representation."""
        if isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8", errors="replace")
        return self.coerce_str(value)


@dataclass(frozen=True)
class PipelineProfileFilters:
    """Profile and side-to-move helpers."""

    def black_profiles_for_source(self, source: str) -> set[str] | None:
        """Return blacklisted profiles for the given source."""
        if source == "lichess":
            return LICHESS_BLACK_PROFILES
        if source == "chesscom":
            return CHESSCOM_BLACK_PROFILES
        return None

    def normalized_profile_for_source(self, settings: Settings, source: str) -> str:
        """Return a normalized profile string for the source."""
        profiles = {
            "lichess": settings.lichess_profile or settings.rapid_perf,
            "chesscom": settings.chesscom.profile or settings.chesscom.time_class,
        }
        raw_profile = profiles.get(source)
        return (raw_profile or "").strip().lower()

    def side_filter_for_profile(self, profile: str, black_profiles: set[str]) -> str | None:
        """Return a side filter for the provided profile."""
        return "black" if profile in black_profiles else None

    def resolve_side_to_move_filter(self, settings: Settings) -> str | None:
        """Resolve the side-to-move filter from settings."""
        source = normalize_string(settings.source)
        profile = self.normalized_profile_for_source(settings, source)
        black_profiles = self.black_profiles_for_source(source)
        if not profile or black_profiles is None:
            return None
        return self.side_filter_for_profile(profile, black_profiles)


@dataclass(frozen=True)
class PipelineEmissions:  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """Emit progress and operational events for pipeline steps."""

    def emit_progress(self, progress: ProgressCallback | None, step: str, **fields: object) -> None:
        """Invoke progress callback with standard payload."""
        if progress is None:
            return
        payload: dict[str, object] = {"step": step, "timestamp": time.time()}
        payload.update(fields)
        progress(payload)

    def emit_fetch_progress(self, ctx: FetchProgressContext) -> None:
        """Emit progress for fetch steps."""
        self.emit_progress(
            ctx.progress,
            "fetch_games",
            source=ctx.settings.source,
            fetched_games=ctx.fetched_games,
            since_ms=ctx.fetch_context.since_ms,
            cursor=ctx.fetch_context.next_cursor or ctx.fetch_context.cursor_value,
            backfill=ctx.backfill_mode,
            backfill_start_ms=ctx.window_start_ms,
            backfill_end_ms=ctx.window_end_ms,
        )

    def emit_positions_ready(
        self,
        settings: Settings,
        progress: ProgressCallback | None,
        positions: list[dict[str, object]],
    ) -> None:
        """Emit progress when positions are ready."""
        self.emit_progress(
            progress,
            "positions_ready",
            source=settings.source,
            positions=len(positions),
        )

    def emit_daily_sync_start(self, ctx: DailySyncStartContext) -> None:
        """Emit progress and ops events for a sync start."""
        self.emit_progress(
            ctx.progress,
            "start",
            source=ctx.settings.source,
            message="Starting pipeline run",
        )
        record_ops_event(
            OpsEvent(
                settings=ctx.settings,
                component=ctx.settings.run_context,
                event_type="daily_game_sync_start",
                source=ctx.settings.source,
                profile=ctx.profile,
                metadata={
                    "backfill": ctx.backfill_mode,
                    "window_start_ms": ctx.window_start_ms,
                    "window_end_ms": ctx.window_end_ms,
                },
            )
        )

    def emit_backfill_window_filtered(
        self,
        settings: Settings,
        progress: ProgressCallback | None,
        filtered: int,
        window_start_ms: int | None,
        window_end_ms: int | None,
    ) -> None:  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Emit progress when backfill windows are filtered."""
        if not filtered:
            return
        logger.info(
            "Filtered %s games outside backfill window for source=%s",
            filtered,
            settings.source,
        )
        self.emit_progress(
            progress,
            "backfill_window_filtered",
            source=settings.source,
            filtered=filtered,
            backfill_start_ms=window_start_ms,
            backfill_end_ms=window_end_ms,
        )

    def maybe_emit_analysis_progress(
        self,
        progress: ProgressCallback | None,
        settings: Settings,
        idx: int,
        total_positions: int,
        progress_every: int,
    ) -> None:  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Emit analysis progress updates when due."""
        if not progress:
            return
        if idx == total_positions - INDEX_OFFSET or (
            (idx + INDEX_OFFSET) % progress_every == ZERO_COUNT
        ):
            self.emit_progress(
                progress,
                "analyze_positions",
                source=settings.source,
                analyzed=idx + INDEX_OFFSET,
                total=total_positions,
            )

    def maybe_emit_window_filtered(self, context: WindowFilterContext) -> None:
        """Emit backfill window metrics when needed."""
        if not context.backfill_mode or not context.window_filtered:
            return
        self.emit_backfill_window_filtered(
            context.settings,
            context.progress,
            context.window_filtered,
            context.window_start_ms,
            context.window_end_ms,
        )

    def log_skipped_backfill(self, settings: Settings, skipped_games: list[GameRow]) -> None:
        """Log skipped historical games in backfill mode."""
        if skipped_games:
            logger.info(
                "Skipping %s historical games already processed for source=%s",
                len(skipped_games),
                settings.source,
            )


@dataclass(frozen=True)
class PipelineNoGames:
    """Handle no-games branches in the pipeline."""

    def no_games_checkpoint(
        self, settings: Settings, backfill_mode: bool, fetch_context: FetchContext
    ) -> int | None:
        """Return the checkpoint value for no-games scenarios."""
        if backfill_mode or settings.source == "chesscom":
            return None
        return fetch_context.since_ms

    def no_games_cursor(self, backfill_mode: bool, fetch_context: FetchContext) -> str | None:
        """Resolve cursors when no games are returned."""
        if backfill_mode:
            return fetch_context.cursor_before
        return fetch_context.next_cursor or fetch_context.cursor_value

    def apply_no_games_dedupe_checkpoint(
        self,
        settings: Settings,
        backfill_mode: bool,
        fetch_context: FetchContext,
        last_timestamp_value: int,
    ) -> tuple[int | None, int]:
        """Apply checkpoint updates when no games were deduped."""
        if backfill_mode:
            return None, last_timestamp_value
        if settings.source == "chesscom":
            write_chesscom_cursor(settings.checkpoint_path, fetch_context.next_cursor)
            return None, last_timestamp_value
        checkpoint_value = max(fetch_context.since_ms, last_timestamp_value)
        write_checkpoint(settings.checkpoint_path, checkpoint_value)
        return checkpoint_value, checkpoint_value

    def build_no_games_payload(self, ctx: NoGamesPayloadContext) -> dict[str, object]:
        """Build payload when no games are fetched."""
        metrics_version = _update_metrics_and_version(ctx.settings, ctx.conn)
        checkpoint_ms = self.no_games_checkpoint(
            ctx.settings,
            ctx.backfill_mode,
            ctx.fetch_context,
        )
        cursor = self.no_games_cursor(ctx.backfill_mode, ctx.fetch_context)
        return {
            "source": ctx.settings.source,
            "user": ctx.settings.user,
            "fetched_games": 0,
            "raw_pgns_inserted": 0,
            "raw_pgns_hashed": 0,
            "raw_pgns_matched": 0,
            "positions": 0,
            "tactics": 0,
            "metrics_version": metrics_version,
            "checkpoint_ms": checkpoint_ms,
            "cursor": cursor,
            "last_timestamp_ms": ctx.last_timestamp_value or ctx.fetch_context.since_ms,
            "since_ms": ctx.fetch_context.since_ms,
            "window_filtered": ctx.window_filtered,
        }

    def build_no_games_after_dedupe_payload(
        self, ctx: NoGamesAfterDedupePayloadContext
    ) -> dict[str, object]:
        """Build payload when no games remain after dedupe."""
        metrics_version = _update_metrics_and_version(ctx.settings, ctx.conn)
        checkpoint_ms, last_timestamp_value = self.apply_no_games_dedupe_checkpoint(
            ctx.settings,
            ctx.backfill_mode,
            ctx.fetch_context,
            ctx.last_timestamp_value,
        )
        return {
            "source": ctx.settings.source,
            "user": ctx.settings.user,
            "fetched_games": len(ctx.games),
            "raw_pgns_inserted": 0,
            "raw_pgns_hashed": 0,
            "raw_pgns_matched": 0,
            "postgres_raw_pgns_inserted": 0,
            "positions": 0,
            "tactics": 0,
            "metrics_version": metrics_version,
            "checkpoint_ms": checkpoint_ms,
            "cursor": self.no_games_cursor(ctx.backfill_mode, ctx.fetch_context),
            "last_timestamp_ms": last_timestamp_value,
            "since_ms": ctx.fetch_context.since_ms,
            "window_filtered": ctx.window_filtered,
        }

    def handle_no_games(self, context: NoGamesContext) -> dict[str, object]:
        """Return the no-games payload and emit progress updates."""
        logger.info(
            "No new games for source=%s at checkpoint=%s",
            context.settings.source,
            context.fetch_context.since_ms,
        )
        EMITTERS.emit_progress(
            context.progress,
            "no_games",
            source=context.settings.source,
            message="No new games to process",
        )
        return self.build_no_games_payload(build_no_games_payload_context(context))

    def handle_no_games_after_dedupe(self, context: NoGamesAfterDedupeContext) -> dict[str, object]:
        """Return the no-games payload after dedupe."""
        logger.info(
            "No new games to process after backfill dedupe for source=%s",
            context.settings.source,
        )
        return self.build_no_games_after_dedupe_payload(
            build_no_games_after_dedupe_payload_context(context)
        )


@dataclass(frozen=True)
class PipelineAnalysisCheckpoint:
    """Read and write analysis checkpoint files."""

    def read_analysis_checkpoint(self, checkpoint_path, signature: str) -> int:
        """Return the checkpoint index for the signature or -1."""
        if not checkpoint_path.exists():
            return -1
        try:
            data = json.loads(checkpoint_path.read_text())
        except json.JSONDecodeError:
            return -1
        if data.get("signature") != signature:
            return -1
        return int(data.get("index", -1))

    def write_analysis_checkpoint(self, checkpoint_path, signature: str, index: int) -> None:
        """Persist analysis checkpoint metadata."""
        payload = {"signature": signature, "index": index}
        checkpoint_path.write_text(json.dumps(payload))

    def clear_analysis_checkpoint(self, checkpoint_path) -> None:
        """Remove analysis checkpoint data."""
        if checkpoint_path.exists():
            checkpoint_path.unlink()

    def maybe_clear_analysis_checkpoint(self, analysis_checkpoint_path) -> None:
        """Clear the analysis checkpoint if a path is provided."""
        if analysis_checkpoint_path is not None:
            self.clear_analysis_checkpoint(analysis_checkpoint_path)

    def maybe_write_analysis_checkpoint(
        self,
        analysis_checkpoint_path,
        analysis_signature: str,
        index: int,
    ) -> None:
        """Write the analysis checkpoint if enabled."""
        if analysis_checkpoint_path is None:
            return
        self.write_analysis_checkpoint(analysis_checkpoint_path, analysis_signature, index)


@dataclass(frozen=True)
class PipelineCheckpointUpdates:  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """Resolve and persist checkpoint metadata."""

    def resolve_last_timestamp_value(self, games: list[GameRow], fallback: int) -> int:
        """Return the last timestamp from games or a fallback value."""
        if not games:
            return fallback
        return latest_timestamp(games) or fallback

    def resolve_chesscom_last_timestamp(
        self,
        fetch_context: FetchContext,
        games: list[GameRow],
        last_timestamp_value: int,
    ) -> int:
        """Resolve last chess.com timestamp values."""
        if fetch_context.chesscom_result:
            return fetch_context.chesscom_result.last_timestamp_ms
        if games:
            return latest_timestamp(games) or last_timestamp_value
        return last_timestamp_value

    def cursor_last_timestamp(self, cursor_value: str | None) -> int:
        """Parse last timestamps from cursor values."""
        if not cursor_value:
            return 0
        try:
            return int(cursor_value.split(":", 1)[0])
        except ValueError:
            return 0

    def update_chesscom_checkpoint(
        self,
        settings: Settings,
        fetch_context: FetchContext,
        games: list[GameRow],
        last_timestamp_value: int,
    ) -> tuple[int | None, int]:
        """Persist cursor and compute updated last timestamp."""
        write_chesscom_cursor(settings.checkpoint_path, fetch_context.next_cursor)
        last_timestamp_value = self.resolve_chesscom_last_timestamp(
            fetch_context,
            games,
            last_timestamp_value,
        )
        return None, last_timestamp_value

    def update_lichess_checkpoint(
        self,
        settings: Settings,
        fetch_context: FetchContext,
        games: list[GameRow],
    ) -> tuple[int | None, int]:
        """Persist and return the updated checkpoint value."""
        checkpoint_value = max(fetch_context.since_ms, latest_timestamp(games))
        write_checkpoint(settings.checkpoint_path, checkpoint_value)
        return checkpoint_value, checkpoint_value

    def update_daily_checkpoint(
        self,
        settings: Settings,
        backfill_mode: bool,
        fetch_context: FetchContext,
        games: list[GameRow],
        last_timestamp_value: int,
    ) -> tuple[int | None, int]:  # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Update daily checkpoint values after sync."""
        if backfill_mode:
            return None, last_timestamp_value
        if settings.source == "chesscom":
            return self.update_chesscom_checkpoint(
                settings,
                fetch_context,
                games,
                last_timestamp_value,
            )
        return self.update_lichess_checkpoint(settings, fetch_context, games)


COERCIONS = PipelineCoercions()
PROFILES = PipelineProfileFilters()
EMITTERS = PipelineEmissions()
NO_GAMES = PipelineNoGames()
ANALYSIS_CHECKPOINTS = PipelineAnalysisCheckpoint()
CHECKPOINT_UPDATES = PipelineCheckpointUpdates()


def _coerce_int(value: object) -> int:
    return COERCIONS.coerce_int(value)


def _coerce_str(value: object) -> str:
    return COERCIONS.coerce_str(value)


def _coerce_pgn(value: object) -> str:
    return COERCIONS.coerce_pgn(value)


def _black_profiles_for_source(source: str) -> set[str] | None:
    return PROFILES.black_profiles_for_source(source)


def _normalized_profile_for_source(settings: Settings, source: str) -> str:
    return PROFILES.normalized_profile_for_source(settings, source)


def _side_filter_for_profile(profile: str, black_profiles: set[str]) -> str | None:
    return PROFILES.side_filter_for_profile(profile, black_profiles)


def _resolve_side_to_move_filter(settings: Settings) -> str | None:
    return PROFILES.resolve_side_to_move_filter(settings)


def _emit_progress(progress: ProgressCallback | None, step: str, **fields: object) -> None:
    EMITTERS.emit_progress(progress, step, **fields)


def _emit_fetch_progress(ctx: FetchProgressContext) -> None:
    EMITTERS.emit_fetch_progress(ctx)


def _emit_positions_ready(
    settings: Settings,
    progress: ProgressCallback | None,
    positions: list[dict[str, object]],
) -> None:
    EMITTERS.emit_positions_ready(settings, progress, positions)


def _emit_daily_sync_start(ctx: DailySyncStartContext) -> None:
    EMITTERS.emit_daily_sync_start(ctx)


def _emit_backfill_window_filtered(
    settings: Settings,
    progress: ProgressCallback | None,
    filtered: int,
    window_start_ms: int | None,
    window_end_ms: int | None,
) -> None:
    EMITTERS.emit_backfill_window_filtered(
        settings,
        progress,
        filtered,
        window_start_ms,
        window_end_ms,
    )


def _maybe_emit_analysis_progress(
    progress: ProgressCallback | None,
    settings: Settings,
    idx: int,
    total_positions: int,
    progress_every: int,
) -> None:
    EMITTERS.maybe_emit_analysis_progress(
        progress,
        settings,
        idx,
        total_positions,
        progress_every,
    )


def _maybe_emit_window_filtered(context: WindowFilterContext) -> None:
    EMITTERS.maybe_emit_window_filtered(context)


def _log_skipped_backfill(settings: Settings, skipped_games: list[GameRow]) -> None:
    EMITTERS.log_skipped_backfill(settings, skipped_games)


def _no_games_checkpoint(
    settings: Settings, backfill_mode: bool, fetch_context: FetchContext
) -> int | None:
    return NO_GAMES.no_games_checkpoint(settings, backfill_mode, fetch_context)


def _no_games_cursor(backfill_mode: bool, fetch_context: FetchContext) -> str | None:
    return NO_GAMES.no_games_cursor(backfill_mode, fetch_context)


def _apply_no_games_dedupe_checkpoint(
    settings: Settings,
    backfill_mode: bool,
    fetch_context: FetchContext,
    last_timestamp_value: int,
) -> tuple[int | None, int]:
    return NO_GAMES.apply_no_games_dedupe_checkpoint(
        settings,
        backfill_mode,
        fetch_context,
        last_timestamp_value,
    )


def _build_no_games_payload(ctx: NoGamesPayloadContext) -> dict[str, object]:
    return NO_GAMES.build_no_games_payload(ctx)


def _build_no_games_after_dedupe_payload(
    ctx: NoGamesAfterDedupePayloadContext,
) -> dict[str, object]:
    return NO_GAMES.build_no_games_after_dedupe_payload(ctx)


def _handle_no_games(context: NoGamesContext) -> dict[str, object]:
    return NO_GAMES.handle_no_games(context)


def _handle_no_games_after_dedupe(context: NoGamesAfterDedupeContext) -> dict[str, object]:
    return NO_GAMES.handle_no_games_after_dedupe(context)


def _read_analysis_checkpoint(checkpoint_path, signature: str) -> int:
    return ANALYSIS_CHECKPOINTS.read_analysis_checkpoint(checkpoint_path, signature)


def _write_analysis_checkpoint(checkpoint_path, signature: str, index: int) -> None:
    ANALYSIS_CHECKPOINTS.write_analysis_checkpoint(checkpoint_path, signature, index)


def _clear_analysis_checkpoint(checkpoint_path) -> None:
    ANALYSIS_CHECKPOINTS.clear_analysis_checkpoint(checkpoint_path)


def _maybe_clear_analysis_checkpoint(analysis_checkpoint_path) -> None:
    ANALYSIS_CHECKPOINTS.maybe_clear_analysis_checkpoint(analysis_checkpoint_path)


def _maybe_write_analysis_checkpoint(
    analysis_checkpoint_path,
    analysis_signature: str,
    index: int,
) -> None:
    ANALYSIS_CHECKPOINTS.maybe_write_analysis_checkpoint(
        analysis_checkpoint_path,
        analysis_signature,
        index,
    )


def _resolve_last_timestamp_value(games: list[GameRow], fallback: int) -> int:
    return CHECKPOINT_UPDATES.resolve_last_timestamp_value(games, fallback)


def _resolve_chesscom_last_timestamp(
    fetch_context: FetchContext,
    games: list[GameRow],
    last_timestamp_value: int,
) -> int:
    return CHECKPOINT_UPDATES.resolve_chesscom_last_timestamp(
        fetch_context,
        games,
        last_timestamp_value,
    )


def _cursor_last_timestamp(cursor_value: str | None) -> int:
    return CHECKPOINT_UPDATES.cursor_last_timestamp(cursor_value)


def _update_chesscom_checkpoint(
    settings: Settings,
    fetch_context: FetchContext,
    games: list[GameRow],
    last_timestamp_value: int,
) -> tuple[int | None, int]:
    return CHECKPOINT_UPDATES.update_chesscom_checkpoint(
        settings,
        fetch_context,
        games,
        last_timestamp_value,
    )


def _update_lichess_checkpoint(
    settings: Settings,
    fetch_context: FetchContext,
    games: list[GameRow],
) -> tuple[int | None, int]:
    return CHECKPOINT_UPDATES.update_lichess_checkpoint(settings, fetch_context, games)


def _update_daily_checkpoint(
    settings: Settings,
    backfill_mode: bool,
    fetch_context: FetchContext,
    games: list[GameRow],
    last_timestamp_value: int,
) -> tuple[int | None, int]:
    return CHECKPOINT_UPDATES.update_daily_checkpoint(
        settings,
        backfill_mode,
        fetch_context,
        games,
        last_timestamp_value,
    )


__all__ = [
    "ANALYSIS_CHECKPOINTS",
    "CHECKPOINT_UPDATES",
    "COERCIONS",
    "EMITTERS",
    "NO_GAMES",
    "PROFILES",
    "PipelineAnalysisCheckpoint",
    "PipelineCheckpointUpdates",
    "PipelineCoercions",
    "PipelineEmissions",
    "PipelineNoGames",
    "PipelineProfileFilters",
    "_apply_no_games_dedupe_checkpoint",
    "_black_profiles_for_source",
    "_build_no_games_after_dedupe_payload",
    "_build_no_games_payload",
    "_clear_analysis_checkpoint",
    "_coerce_int",
    "_coerce_pgn",
    "_coerce_str",
    "_cursor_last_timestamp",
    "_emit_backfill_window_filtered",
    "_emit_daily_sync_start",
    "_emit_fetch_progress",
    "_emit_positions_ready",
    "_emit_progress",
    "_handle_no_games",
    "_handle_no_games_after_dedupe",
    "_log_skipped_backfill",
    "_maybe_clear_analysis_checkpoint",
    "_maybe_emit_analysis_progress",
    "_maybe_emit_window_filtered",
    "_maybe_write_analysis_checkpoint",
    "_no_games_checkpoint",
    "_no_games_cursor",
    "_normalized_profile_for_source",
    "_read_analysis_checkpoint",
    "_resolve_chesscom_last_timestamp",
    "_resolve_last_timestamp_value",
    "_resolve_side_to_move_filter",
    "_side_filter_for_profile",
    "_update_chesscom_checkpoint",
    "_update_daily_checkpoint",
    "_update_lichess_checkpoint",
    "_write_analysis_checkpoint",
]
