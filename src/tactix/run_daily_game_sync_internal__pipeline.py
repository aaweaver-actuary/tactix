"""Run the daily game sync pipeline."""

from __future__ import annotations

from tactix.analysis_context import AnalysisAndMetricsContext
from tactix.apply_backfill_filter__pipeline import _apply_backfill_filter
from tactix.build_daily_sync_payload__pipeline import _build_daily_sync_payload
from tactix.DailySyncCompleteContext import DailySyncCompleteContext
from tactix.DailySyncStartContext import (
    DailyGameSyncContext,
    DailySyncPayloadContext,
    DailySyncStartContext,
    NoGamesAfterDedupeContext,
    NoGamesContext,
    PrepareGamesForSyncContext,
)
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.emit_daily_sync_start__pipeline import _emit_daily_sync_start
from tactix.emit_positions_ready__pipeline import _emit_positions_ready
from tactix.handle_no_games__pipeline import _handle_no_games
from tactix.handle_no_games_after_dedupe__pipeline import _handle_no_games_after_dedupe
from tactix.is_backfill_mode__pipeline import _is_backfill_mode
from tactix.log_raw_pgns_persisted__pipeline import _log_raw_pgns_persisted
from tactix.log_skipped_backfill__pipeline import _log_skipped_backfill
from tactix.prepare_analysis_inputs__pipeline import _prepare_analysis_inputs
from tactix.prepare_games_for_sync__pipeline import _prepare_games_for_sync
from tactix.record_daily_sync_complete__pipeline import _record_daily_sync_complete
from tactix.run_analysis_and_metrics__pipeline import _run_analysis_and_metrics
from tactix.update_daily_checkpoint__pipeline import _update_daily_checkpoint


def _run_daily_game_sync(
    context: DailyGameSyncContext,
) -> dict[str, object]:
    backfill_mode = _is_backfill_mode(context.window_start_ms, context.window_end_ms)
    _emit_daily_sync_start(
        DailySyncStartContext(
            settings=context.settings,
            progress=context.progress,
            profile=context.profile,
            backfill_mode=backfill_mode,
            window_start_ms=context.window_start_ms,
            window_end_ms=context.window_end_ms,
        )
    )
    games, fetch_context, window_filtered, last_timestamp_value = _prepare_games_for_sync(
        PrepareGamesForSyncContext(
            settings=context.settings,
            client=context.client,
            backfill_mode=backfill_mode,
            window_start_ms=context.window_start_ms,
            window_end_ms=context.window_end_ms,
            progress=context.progress,
        )
    )
    conn = get_connection(context.settings.duckdb_path)
    init_schema(conn)
    if not games:
        return _handle_no_games(
            NoGamesContext(
                settings=context.settings,
                conn=conn,
                progress=context.progress,
                backfill_mode=backfill_mode,
                fetch_context=fetch_context,
                last_timestamp_value=last_timestamp_value,
                window_filtered=window_filtered,
            )
        )
    games_to_process, skipped_games = _apply_backfill_filter(
        conn,
        games,
        backfill_mode,
        context.settings.source,
    )
    _log_skipped_backfill(context.settings, skipped_games)
    if not games_to_process:
        return _handle_no_games_after_dedupe(
            NoGamesAfterDedupeContext(
                settings=context.settings,
                conn=conn,
                progress=context.progress,
                backfill_mode=backfill_mode,
                fetch_context=fetch_context,
                last_timestamp_value=last_timestamp_value,
                games=games,
                window_filtered=window_filtered,
            )
        )
    analysis_prep = _prepare_analysis_inputs(
        conn,
        context.settings,
        games_to_process,
        context.progress,
        context.profile,
    )
    _log_raw_pgns_persisted(
        context.settings,
        analysis_prep.raw_pgns_inserted,
        analysis_prep.raw_pgns_hashed,
        analysis_prep.raw_pgns_matched,
        games_to_process,
    )
    _emit_positions_ready(context.settings, context.progress, analysis_prep.positions)
    analysis_result = _run_analysis_and_metrics(
        AnalysisAndMetricsContext(
            conn=conn,
            settings=context.settings,
            positions=analysis_prep.positions,
            resume_index=analysis_prep.resume_index,
            analysis_signature=analysis_prep.analysis_signature,
            progress=context.progress,
            profile=context.profile,
        )
    )
    checkpoint_value, last_timestamp_value = _update_daily_checkpoint(
        context.settings,
        backfill_mode,
        fetch_context,
        games,
        last_timestamp_value,
    )
    _record_daily_sync_complete(
        DailySyncCompleteContext(
            settings=context.settings,
            profile=context.profile,
            games=games,
            raw_pgns_inserted=analysis_prep.raw_pgns_inserted,
            postgres_raw_pgns_inserted=analysis_prep.postgres_raw_pgns_inserted,
            positions_count=analysis_result.total_positions,
            tactics_count=analysis_result.tactics_count,
            postgres_written=analysis_result.postgres_written,
            postgres_synced=analysis_result.postgres_synced,
            metrics_version=analysis_result.metrics_version,
            backfill_mode=backfill_mode,
        )
    )
    return _build_daily_sync_payload(
        DailySyncPayloadContext(
            settings=context.settings,
            fetch_context=fetch_context,
            games=games,
            raw_pgns_inserted=analysis_prep.raw_pgns_inserted,
            raw_pgns_hashed=analysis_prep.raw_pgns_hashed,
            raw_pgns_matched=analysis_prep.raw_pgns_matched,
            postgres_raw_pgns_inserted=analysis_prep.postgres_raw_pgns_inserted,
            positions_count=analysis_result.total_positions,
            tactics_count=analysis_result.tactics_count,
            metrics_version=analysis_result.metrics_version,
            checkpoint_value=checkpoint_value,
            last_timestamp_value=last_timestamp_value,
            backfill_mode=backfill_mode,
        )
    )
