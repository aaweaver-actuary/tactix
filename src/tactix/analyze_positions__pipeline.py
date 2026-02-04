from __future__ import annotations

from tactix.AnalysisLoopContext import AnalysisLoopContext
from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import INDEX_OFFSET, RESUME_INDEX_START
from tactix.init_analysis_schema_if_needed__pipeline import _init_analysis_schema_if_needed
from tactix.maybe_sync_analysis_results__pipeline import _maybe_sync_analysis_results
from tactix.ops_event import OpsEvent
from tactix.postgres_analysis_enabled import postgres_analysis_enabled
from tactix.postgres_connection import postgres_connection
from tactix.record_ops_event import record_ops_event
from tactix.run_analysis_loop__pipeline import _run_analysis_loop
from tactix.utils.logger import funclogger


@funclogger
def _analyze_positions(
    conn,
    settings: Settings,
    positions: list[dict[str, object]],
) -> tuple[int, int]:
    if not positions:
        return 0, 0
    analysis_pg_enabled = postgres_analysis_enabled(settings)
    with postgres_connection(settings) as pg_conn:
        _init_analysis_schema_if_needed(pg_conn, analysis_pg_enabled)
        tactics_detected, postgres_written = _run_analysis_loop(
            AnalysisLoopContext(
                conn=conn,
                settings=settings,
                positions=positions,
                resume_index=RESUME_INDEX_START - INDEX_OFFSET,
                analysis_checkpoint_path=None,
                analysis_signature="",
                progress=None,
                pg_conn=pg_conn,
                analysis_pg_enabled=analysis_pg_enabled,
            )
        )
        postgres_synced, postgres_written = _maybe_sync_analysis_results(
            conn,
            settings,
            pg_conn,
            analysis_pg_enabled,
            postgres_written,
        )
    positions_analyzed = len(positions)
    record_ops_event(
        OpsEvent(
            settings=settings,
            component="analysis",
            event_type="analysis_complete",
            source=settings.source,
            profile=settings.lichess_profile or settings.chesscom.profile,
            metadata={
                "positions_analyzed": positions_analyzed,
                "tactics_detected": tactics_detected,
                "postgres_tactics_written": postgres_written,
                "postgres_tactics_synced": postgres_synced,
            },
        )
    )
    return positions_analyzed, tactics_detected
