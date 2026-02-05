"""Pipeline orchestrators for analysis and sync flows."""

from __future__ import annotations

import time

import chess.engine

from tactix.analyse_with_retries__pipeline import _analyse_with_retries
from tactix.analysis_progress_interval__pipeline import _analysis_progress_interval
from tactix.analysis_signature__pipeline import _analysis_signature
from tactix.AnalysisPrepResult import AnalysisPrepResult
from tactix.analyze_position import analyze_position
from tactix.analyze_positions__pipeline import _analyze_positions
from tactix.analyze_positions_with_progress__pipeline import (
    _analyze_positions_with_progress,
)
from tactix.app.use_cases.pipeline_support import (
    _apply_no_games_dedupe_checkpoint,
    _black_profiles_for_source,
    _build_no_games_after_dedupe_payload,
    _build_no_games_payload,
    _clear_analysis_checkpoint,
    _coerce_int,
    _coerce_pgn,
    _coerce_str,
    _cursor_last_timestamp,
    _emit_backfill_window_filtered,
    _emit_daily_sync_start,
    _emit_fetch_progress,
    _emit_positions_ready,
    _emit_progress,
    _handle_no_games,
    _handle_no_games_after_dedupe,
    _log_skipped_backfill,
    _maybe_clear_analysis_checkpoint,
    _maybe_emit_analysis_progress,
    _maybe_emit_window_filtered,
    _maybe_write_analysis_checkpoint,
    _no_games_checkpoint,
    _no_games_cursor,
    _normalized_profile_for_source,
    _read_analysis_checkpoint,
    _resolve_chesscom_last_timestamp,
    _resolve_last_timestamp_value,
    _resolve_side_to_move_filter,
    _side_filter_for_profile,
    _update_chesscom_checkpoint,
    _update_daily_checkpoint,
    _update_lichess_checkpoint,
    _write_analysis_checkpoint,
)
from tactix.apply_backfill_filter__pipeline import _apply_backfill_filter
from tactix.attach_position_ids__pipeline import _attach_position_ids
from tactix.build_chess_client__pipeline import _build_chess_client
from tactix.build_chunk_row__pipeline import _build_chunk_row
from tactix.build_daily_sync_payload__pipeline import _build_daily_sync_payload
from tactix.build_pipeline_settings__pipeline import _build_pipeline_settings
from tactix.chesscom_raw_games__pipeline import _chesscom_raw_games
from tactix.collect_game_ids__pipeline import _collect_game_ids
from tactix.collect_positions_for_monitor__pipeline import _collect_positions_for_monitor
from tactix.compute_pgn_hashes__pipeline import _compute_pgn_hashes
from tactix.config import Settings
from tactix.conversion_payload__pipeline import _conversion_payload
from tactix.convert_raw_pgns_to_positions__pipeline import convert_raw_pgns_to_positions
from tactix.count_hash_matches__pipeline import _count_hash_matches
from tactix.DailyAnalysisResult import DailyAnalysisResult
from tactix.db.duckdb_store import fetch_position_counts
from tactix.db.raw_pgn_repository_provider import fetch_latest_pgn_hashes, hash_pgn
from tactix.dedupe_games__pipeline import _dedupe_games
from tactix.define_pipeline_state__pipeline import (
    ANALYSIS_PROGRESS_BUCKETS,
    CHESSCOM_BLACK_PROFILES,
    DEFAULT_SYNC_LIMIT,
    INDEX_OFFSET,
    LICHESS_BLACK_PROFILES,
    RESUME_INDEX_START,
    SINGLE_PGN_CHUNK,
    ZERO_COUNT,
    ProgressCallback,
    logger,
)
from tactix.empty_conversion_payload__pipeline import _empty_conversion_payload
from tactix.expand_pgn_rows__pipeline import _expand_pgn_rows
from tactix.expand_single_pgn_row__pipeline import _expand_single_pgn_row
from tactix.extract_positions_for_new_games__pipeline import (
    _extract_positions_for_new_games,
)
from tactix.extract_positions_for_rows__pipeline import _extract_positions_for_rows
from tactix.extract_positions_from_games__pipeline import _extract_positions_from_games
from tactix.fetch_chesscom_games__pipeline import _fetch_chesscom_games
from tactix.fetch_incremental_games__pipeline import _fetch_incremental_games
from tactix.fetch_lichess_games__pipeline import _fetch_lichess_games
from tactix.FetchContext import FetchContext
from tactix.filter_backfill_games__pipeline import _filter_backfill_games
from tactix.filter_games_by_window__pipeline import _filter_games_by_window
from tactix.filter_games_for_window__pipeline import _filter_games_for_window
from tactix.filter_positions_to_process__pipeline import _filter_positions_to_process
from tactix.filter_unprocessed_games__pipeline import _filter_unprocessed_games
from tactix.GameRow import GameRow
from tactix.get_dashboard_payload__pipeline import get_dashboard_payload
from tactix.init_analysis_schema_if_needed__pipeline import _init_analysis_schema_if_needed
from tactix.is_backfill_mode__pipeline import _is_backfill_mode
from tactix.load_resume_positions__pipeline import _load_resume_positions
from tactix.log_raw_pgns_persisted__pipeline import _log_raw_pgns_persisted
from tactix.maybe_sync_analysis_results__pipeline import _maybe_sync_analysis_results
from tactix.maybe_upsert_postgres_analysis__pipeline import _maybe_upsert_postgres_analysis
from tactix.normalize_and_expand_games__pipeline import _normalize_and_expand_games
from tactix.normalize_game_row__pipeline import _normalize_game_row
from tactix.persist_and_extract_positions__pipeline import _persist_and_extract_positions
from tactix.persist_raw_pgns__pipeline import _persist_raw_pgns
from tactix.prepare_analysis_inputs__pipeline import _prepare_analysis_inputs
from tactix.prepare_games_for_sync__pipeline import _prepare_games_for_sync
from tactix.process_analysis_position__pipeline import _process_analysis_position
from tactix.raise_for_hash_mismatch__pipeline import _raise_for_hash_mismatch
from tactix.record_daily_sync_complete__pipeline import _record_daily_sync_complete
from tactix.refresh_raw_pgns_for_existing_positions__pipeline import (
    _refresh_raw_pgns_for_existing_positions,
)
from tactix.request_chesscom_games__pipeline import _request_chesscom_games
from tactix.run_analysis_and_metrics__pipeline import _run_analysis_and_metrics
from tactix.run_analysis_loop__pipeline import _run_analysis_loop
from tactix.run_daily_game_sync__pipeline import _run_daily_game_sync, run_daily_game_sync
from tactix.run_migrations__pipeline import run_migrations
from tactix.run_monitor_new_positions__pipeline import run_monitor_new_positions
from tactix.run_refresh_metrics__pipeline import run_refresh_metrics
from tactix.should_skip_backfill__pipeline import _should_skip_backfill
from tactix.StockfishEngine import StockfishEngine
from tactix.sync_postgres_analysis_results__pipeline import _sync_postgres_analysis_results
from tactix.update_metrics_and_version__pipeline import _update_metrics_and_version
from tactix.upsert_analysis_tactic_with_outcome import upsert_analysis_tactic_with_outcome
from tactix.upsert_postgres_raw_pgns_if_enabled__pipeline import (
    _upsert_postgres_raw_pgns_if_enabled,
)
from tactix.validate_raw_pgn_hashes__pipeline import _validate_raw_pgn_hashes
from tactix.within_window__pipeline import _within_window


def analyse_with_retries(
    engine,
    position: dict[str, object],
    settings: Settings,
) -> tuple[dict[str, object], dict[str, object]] | None:
    return _analyse_with_retries(engine, position, settings)


__all__ = [
    "ANALYSIS_PROGRESS_BUCKETS",
    "CHESSCOM_BLACK_PROFILES",
    "DEFAULT_SYNC_LIMIT",
    "INDEX_OFFSET",
    "LICHESS_BLACK_PROFILES",
    "RESUME_INDEX_START",
    "SINGLE_PGN_CHUNK",
    "ZERO_COUNT",
    "AnalysisPrepResult",
    "DailyAnalysisResult",
    "FetchContext",
    "GameRow",
    "ProgressCallback",
    "StockfishEngine",
    "_analyse_with_retries",
    "_analysis_progress_interval",
    "_analysis_signature",
    "_analyze_positions",
    "_analyze_positions_with_progress",
    "_apply_backfill_filter",
    "_apply_no_games_dedupe_checkpoint",
    "_attach_position_ids",
    "_black_profiles_for_source",
    "_build_chess_client",
    "_build_chunk_row",
    "_build_daily_sync_payload",
    "_build_no_games_after_dedupe_payload",
    "_build_no_games_payload",
    "_build_pipeline_settings",
    "_chesscom_raw_games",
    "_clear_analysis_checkpoint",
    "_coerce_int",
    "_coerce_pgn",
    "_coerce_str",
    "_collect_game_ids",
    "_collect_positions_for_monitor",
    "_compute_pgn_hashes",
    "_conversion_payload",
    "_count_hash_matches",
    "_cursor_last_timestamp",
    "_dedupe_games",
    "_emit_backfill_window_filtered",
    "_emit_daily_sync_start",
    "_emit_fetch_progress",
    "_emit_positions_ready",
    "_emit_progress",
    "_empty_conversion_payload",
    "_expand_pgn_rows",
    "_expand_single_pgn_row",
    "_extract_positions_for_new_games",
    "_extract_positions_for_rows",
    "_extract_positions_from_games",
    "_fetch_chesscom_games",
    "_fetch_incremental_games",
    "_fetch_lichess_games",
    "_filter_backfill_games",
    "_filter_games_by_window",
    "_filter_games_for_window",
    "_filter_positions_to_process",
    "_filter_unprocessed_games",
    "_handle_no_games",
    "_handle_no_games_after_dedupe",
    "_init_analysis_schema_if_needed",
    "_is_backfill_mode",
    "_load_resume_positions",
    "_log_raw_pgns_persisted",
    "_log_skipped_backfill",
    "_maybe_clear_analysis_checkpoint",
    "_maybe_emit_analysis_progress",
    "_maybe_emit_window_filtered",
    "_maybe_sync_analysis_results",
    "_maybe_upsert_postgres_analysis",
    "_maybe_write_analysis_checkpoint",
    "_no_games_checkpoint",
    "_no_games_cursor",
    "_normalize_and_expand_games",
    "_normalize_game_row",
    "_normalized_profile_for_source",
    "_persist_and_extract_positions",
    "_persist_raw_pgns",
    "_prepare_analysis_inputs",
    "_prepare_games_for_sync",
    "_process_analysis_position",
    "_raise_for_hash_mismatch",
    "_read_analysis_checkpoint",
    "_record_daily_sync_complete",
    "_refresh_raw_pgns_for_existing_positions",
    "_request_chesscom_games",
    "_resolve_chesscom_last_timestamp",
    "_resolve_last_timestamp_value",
    "_resolve_side_to_move_filter",
    "_run_analysis_and_metrics",
    "_run_analysis_loop",
    "_run_daily_game_sync",
    "_should_skip_backfill",
    "_side_filter_for_profile",
    "_sync_postgres_analysis_results",
    "_update_chesscom_checkpoint",
    "_update_daily_checkpoint",
    "_update_lichess_checkpoint",
    "_update_metrics_and_version",
    "_upsert_postgres_raw_pgns_if_enabled",
    "_validate_raw_pgn_hashes",
    "_within_window",
    "_write_analysis_checkpoint",
    "analyse_with_retries",
    "analyze_position",
    "chess",
    "convert_raw_pgns_to_positions",
    "fetch_latest_pgn_hashes",
    "fetch_position_counts",
    "get_dashboard_payload",
    "hash_pgn",
    "logger",
    "run_daily_game_sync",
    "run_migrations",
    "run_monitor_new_positions",
    "run_refresh_metrics",
    "time",
    "upsert_analysis_tactic_with_outcome",
]
