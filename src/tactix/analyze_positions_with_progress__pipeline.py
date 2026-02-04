"""Run analysis loop with progress reporting and Postgres sync."""

from __future__ import annotations

from tactix.analysis_context import AnalysisRunContext
from tactix.AnalysisLoopContext import AnalysisLoopContext
from tactix.init_analysis_schema_if_needed__pipeline import _init_analysis_schema_if_needed
from tactix.maybe_clear_analysis_checkpoint__pipeline import _maybe_clear_analysis_checkpoint
from tactix.maybe_sync_analysis_results__pipeline import _maybe_sync_analysis_results
from tactix.postgres_analysis_enabled import postgres_analysis_enabled
from tactix.postgres_connection import postgres_connection
from tactix.run_analysis_loop__pipeline import _run_analysis_loop
from tactix.utils.logger import funclogger


@funclogger
def _analyze_positions_with_progress(
    ctx: AnalysisRunContext,
) -> tuple[int, int, int]:
    analysis_pg_enabled = postgres_analysis_enabled(ctx.settings)
    with postgres_connection(ctx.settings) as pg_conn:
        _init_analysis_schema_if_needed(pg_conn, analysis_pg_enabled)
        tactics_count, postgres_written = _run_analysis_loop(
            AnalysisLoopContext(
                conn=ctx.conn,
                settings=ctx.settings,
                positions=ctx.positions,
                resume_index=ctx.resume_index,
                analysis_checkpoint_path=ctx.settings.analysis_checkpoint_path,
                analysis_signature=ctx.analysis_signature,
                progress=ctx.progress,
                pg_conn=pg_conn,
                analysis_pg_enabled=analysis_pg_enabled,
            )
        )
        postgres_synced, postgres_written = _maybe_sync_analysis_results(
            ctx.conn,
            ctx.settings,
            pg_conn,
            analysis_pg_enabled,
            postgres_written,
        )
    _maybe_clear_analysis_checkpoint(ctx.settings.analysis_checkpoint_path)
    return tactics_count, postgres_written, postgres_synced
