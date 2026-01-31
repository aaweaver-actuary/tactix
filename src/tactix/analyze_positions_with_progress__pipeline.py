from __future__ import annotations

from tactix.config import Settings
from tactix.init_analysis_schema_if_needed__pipeline import _init_analysis_schema_if_needed
from tactix.maybe_clear_analysis_checkpoint__pipeline import _maybe_clear_analysis_checkpoint
from tactix.maybe_sync_analysis_results__pipeline import _maybe_sync_analysis_results
from tactix.pipeline_state__pipeline import ProgressCallback
from tactix.postgres_store import postgres_analysis_enabled, postgres_connection
from tactix.run_analysis_loop__pipeline import _run_analysis_loop


def _analyze_positions_with_progress(
    conn,
    settings: Settings,
    positions: list[dict[str, object]],
    resume_index: int,
    analysis_checkpoint_path,
    analysis_signature: str,
    progress: ProgressCallback | None,
) -> tuple[int, int, int]:
    analysis_pg_enabled = postgres_analysis_enabled(settings)
    with postgres_connection(settings) as pg_conn:
        _init_analysis_schema_if_needed(pg_conn, analysis_pg_enabled)
        tactics_count, postgres_written = _run_analysis_loop(
            conn,
            settings,
            positions,
            resume_index,
            analysis_checkpoint_path,
            analysis_signature,
            progress,
            pg_conn,
            analysis_pg_enabled,
        )
        postgres_synced, postgres_written = _maybe_sync_analysis_results(
            conn,
            settings,
            pg_conn,
            analysis_pg_enabled,
            postgres_written,
        )
    _maybe_clear_analysis_checkpoint(analysis_checkpoint_path)
    return tactics_count, postgres_written, postgres_synced
