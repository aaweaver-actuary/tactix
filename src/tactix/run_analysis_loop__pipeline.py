"""Run the analysis loop over extracted positions."""

# pylint: disable=import-outside-toplevel

from __future__ import annotations

from tactix.analysis_context import AnalysisPositionContext
from tactix.analysis_progress_interval__pipeline import _analysis_progress_interval
from tactix.AnalysisLoopContext import AnalysisLoopContext
from tactix.process_analysis_position__pipeline import _process_analysis_position


def _run_analysis_loop(
    context: AnalysisLoopContext,
) -> tuple[int, int]:
    """Execute analysis over positions and return counters."""
    total_positions = len(context.positions)
    progress_every = _analysis_progress_interval(total_positions)
    tactics_count = 0
    postgres_written = 0
    from tactix import StockfishEngine as StockfishEngineModule  # noqa: PLC0415

    with StockfishEngineModule.StockfishEngine(context.settings) as engine:
        for idx, pos in enumerate(context.positions):
            tactics_delta, postgres_delta = _process_analysis_position(
                AnalysisPositionContext(
                    conn=context.conn,
                    settings=context.settings,
                    engine=engine,
                    pos=pos,
                    idx=idx,
                    resume_index=context.resume_index,
                    analysis_checkpoint_path=context.analysis_checkpoint_path,
                    analysis_signature=context.analysis_signature,
                    progress=context.progress,
                    total_positions=total_positions,
                    progress_every=progress_every,
                    pg_conn=context.pg_conn,
                    analysis_pg_enabled=context.analysis_pg_enabled,
                )
            )
            tactics_count += tactics_delta
            postgres_written += postgres_delta
    return tactics_count, postgres_written
