from __future__ import annotations

from tactix.config import Settings
from tactix.db.duckdb_store import upsert_tactic_with_outcome
from tactix.define_pipeline_state__pipeline import ProgressCallback
from tactix.maybe_emit_analysis_progress__pipeline import _maybe_emit_analysis_progress
from tactix.maybe_upsert_postgres_analysis__pipeline import _maybe_upsert_postgres_analysis
from tactix.maybe_write_analysis_checkpoint__pipeline import _maybe_write_analysis_checkpoint
from tactix.StockfishEngine import StockfishEngine


def _process_analysis_position(
    conn,
    settings: Settings,
    engine: StockfishEngine,
    pos: dict[str, object],
    idx: int,
    resume_index: int,
    analysis_checkpoint_path,
    analysis_signature: str,
    progress: ProgressCallback | None,
    total_positions: int,
    progress_every: int,
    pg_conn,
    analysis_pg_enabled: bool,
) -> tuple[int, int]:
    if idx <= resume_index:
        return 0, 0
    from tactix import pipeline as pipeline_module  # noqa: PLC0415

    result = pipeline_module._analyse_with_retries(engine, pos, settings)
    if result is None:
        _maybe_write_analysis_checkpoint(analysis_checkpoint_path, analysis_signature, idx)
        return 0, 0
    tactic_row, outcome_row = result
    upsert_tactic_with_outcome(conn, tactic_row, outcome_row)
    postgres_delta = (
        1
        if _maybe_upsert_postgres_analysis(pg_conn, analysis_pg_enabled, tactic_row, outcome_row)
        else 0
    )
    _maybe_write_analysis_checkpoint(analysis_checkpoint_path, analysis_signature, idx)
    _maybe_emit_analysis_progress(progress, settings, idx, total_positions, progress_every)
    return 1, postgres_delta
