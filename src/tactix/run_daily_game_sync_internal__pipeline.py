from __future__ import annotations

from tactix.apply_backfill_filter__pipeline import _apply_backfill_filter
from tactix.build_daily_sync_payload__pipeline import _build_daily_sync_payload
from tactix.chess_clients.base_chess_client import BaseChessClient
from tactix.config import Settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.define_pipeline_state__pipeline import ProgressCallback
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
    settings: Settings,
    client: BaseChessClient,
    progress: ProgressCallback | None,
    window_start_ms: int | None,
    window_end_ms: int | None,
    profile: str | None,
) -> dict[str, object]:
    backfill_mode = _is_backfill_mode(window_start_ms, window_end_ms)
    _emit_daily_sync_start(
        settings,
        progress,
        profile,
        backfill_mode,
        window_start_ms,
        window_end_ms,
    )
    games, fetch_context, window_filtered, last_timestamp_value = _prepare_games_for_sync(
        settings,
        client,
        backfill_mode,
        window_start_ms,
        window_end_ms,
        progress,
    )
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    if not games:
        return _handle_no_games(
            settings,
            conn,
            progress,
            backfill_mode,
            fetch_context,
            last_timestamp_value,
            window_filtered,
        )
    games_to_process, skipped_games = _apply_backfill_filter(
        conn, games, backfill_mode, settings.source
    )
    _log_skipped_backfill(settings, skipped_games)
    if not games_to_process:
        return _handle_no_games_after_dedupe(
            settings,
            conn,
            backfill_mode,
            fetch_context,
            last_timestamp_value,
            games,
            window_filtered,
        )
    analysis_prep = _prepare_analysis_inputs(
        conn,
        settings,
        games_to_process,
        progress,
        profile,
    )
    analysis_checkpoint_path = settings.analysis_checkpoint_path
    _log_raw_pgns_persisted(
        settings,
        analysis_prep.raw_pgns_inserted,
        analysis_prep.raw_pgns_hashed,
        analysis_prep.raw_pgns_matched,
        games_to_process,
    )
    _emit_positions_ready(settings, progress, analysis_prep.positions)
    analysis_result = _run_analysis_and_metrics(
        conn,
        settings,
        analysis_prep.positions,
        analysis_prep.resume_index,
        analysis_checkpoint_path,
        analysis_prep.analysis_signature,
        progress,
        profile,
    )
    checkpoint_value, last_timestamp_value = _update_daily_checkpoint(
        settings,
        backfill_mode,
        fetch_context,
        games,
        last_timestamp_value,
    )
    _record_daily_sync_complete(
        settings,
        profile,
        games,
        analysis_prep.raw_pgns_inserted,
        analysis_prep.postgres_raw_pgns_inserted,
        analysis_result.total_positions,
        analysis_result.tactics_count,
        analysis_result.postgres_written,
        analysis_result.postgres_synced,
        analysis_result.metrics_version,
        backfill_mode,
    )
    return _build_daily_sync_payload(
        settings,
        fetch_context,
        games,
        analysis_prep.raw_pgns_inserted,
        analysis_prep.raw_pgns_hashed,
        analysis_prep.raw_pgns_matched,
        analysis_prep.postgres_raw_pgns_inserted,
        analysis_result.total_positions,
        analysis_result.tactics_count,
        analysis_result.metrics_version,
        checkpoint_value,
        last_timestamp_value,
        backfill_mode,
    )
