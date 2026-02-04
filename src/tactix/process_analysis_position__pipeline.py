from __future__ import annotations

from tactix.analysis_context import AnalysisPositionContext
from tactix.db.duckdb_store import upsert_tactic_with_outcome
from tactix.maybe_emit_analysis_progress__pipeline import _maybe_emit_analysis_progress
from tactix.maybe_upsert_postgres_analysis__pipeline import _maybe_upsert_postgres_analysis
from tactix.maybe_write_analysis_checkpoint__pipeline import _maybe_write_analysis_checkpoint


def _process_analysis_position(
    context: AnalysisPositionContext,
) -> tuple[int, int]:
    if context.idx <= context.resume_index:
        return 0, 0
    from importlib import import_module  # noqa: PLC0415

    pipeline_module = import_module("tactix.pipeline")
    result = pipeline_module.analyse_with_retries(
        context.engine,
        context.pos,
        context.settings,
    )
    if result is None:
        _maybe_write_analysis_checkpoint(
            context.analysis_checkpoint_path,
            context.analysis_signature,
            context.idx,
        )
        return 0, 0
    tactic_row, outcome_row = result
    upsert_tactic_with_outcome(context.conn, tactic_row, outcome_row)
    postgres_delta = (
        1
        if _maybe_upsert_postgres_analysis(
            context.pg_conn,
            context.analysis_pg_enabled,
            tactic_row,
            outcome_row,
        )
        else 0
    )
    _maybe_write_analysis_checkpoint(
        context.analysis_checkpoint_path,
        context.analysis_signature,
        context.idx,
    )
    _maybe_emit_analysis_progress(
        context.progress,
        context.settings,
        context.idx,
        context.total_positions,
        context.progress_every,
    )
    return 1, postgres_delta
