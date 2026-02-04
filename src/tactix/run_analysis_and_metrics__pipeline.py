"""Run analysis and refresh metrics."""

from __future__ import annotations

from tactix.analysis_context import (
    AnalysisAndMetricsContext,
    AnalysisRunContext,
    AnalysisRunInputs,
)
from tactix.analyze_positions_with_progress__pipeline import _analyze_positions_with_progress
from tactix.emit_progress__pipeline import _emit_progress
from tactix.ops_event import OpsEvent
from tactix.pipeline_state__pipeline import DailyAnalysisResult
from tactix.record_ops_event import record_ops_event
from tactix.update_metrics_and_version__pipeline import _update_metrics_and_version


def _run_analysis_and_metrics(
    ctx: AnalysisAndMetricsContext,
) -> DailyAnalysisResult:
    """Run analysis and metrics refresh for a batch."""
    total_positions = len(ctx.positions)
    tactics_count, postgres_written, postgres_synced = _analyze_positions_with_progress(
        AnalysisRunContext(
            conn=ctx.conn,
            settings=ctx.settings,
            run=AnalysisRunInputs(
                positions=ctx.positions,
                resume_index=ctx.resume_index,
                analysis_signature=ctx.analysis_signature,
                progress=ctx.progress,
            ),
        )
    )
    record_ops_event(
        OpsEvent(
            settings=ctx.settings,
            component="analysis",
            event_type="analysis_complete",
            source=ctx.settings.source,
            profile=ctx.profile,
            metadata={
                "positions_analyzed": total_positions,
                "tactics_detected": tactics_count,
                "resume_index": ctx.resume_index,
                "postgres_tactics_written": postgres_written,
                "postgres_tactics_synced": postgres_synced,
            },
        )
    )
    metrics_version = _update_metrics_and_version(ctx.settings, ctx.conn)
    _emit_progress(
        ctx.progress,
        "metrics_refreshed",
        source=ctx.settings.source,
        metrics_version=metrics_version,
        message="Metrics refreshed",
    )
    return DailyAnalysisResult(
        total_positions=total_positions,
        tactics_count=tactics_count,
        postgres_written=postgres_written,
        postgres_synced=postgres_synced,
        metrics_version=metrics_version,
    )
