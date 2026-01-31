from __future__ import annotations

from tactix.analyze_positions_with_progress__pipeline import _analyze_positions_with_progress
from tactix.config import Settings
from tactix.emit_progress__pipeline import _emit_progress
from tactix.pipeline_state__pipeline import DailyAnalysisResult, ProgressCallback
from tactix.postgres_store import record_ops_event
from tactix.update_metrics_and_version__pipeline import _update_metrics_and_version


def _run_analysis_and_metrics(
    conn,
    settings: Settings,
    positions: list[dict[str, object]],
    resume_index: int,
    analysis_checkpoint_path,
    analysis_signature: str,
    progress: ProgressCallback | None,
    profile: str | None,
) -> DailyAnalysisResult:
    total_positions = len(positions)
    tactics_count, postgres_written, postgres_synced = _analyze_positions_with_progress(
        conn,
        settings,
        positions,
        resume_index,
        analysis_checkpoint_path,
        analysis_signature,
        progress,
    )
    record_ops_event(
        settings,
        component="analysis",
        event_type="analysis_complete",
        source=settings.source,
        profile=profile,
        metadata={
            "positions_analyzed": total_positions,
            "tactics_detected": tactics_count,
            "resume_index": resume_index,
            "postgres_tactics_written": postgres_written,
            "postgres_tactics_synced": postgres_synced,
        },
    )
    metrics_version = _update_metrics_and_version(settings, conn)
    _emit_progress(
        progress,
        "metrics_refreshed",
        source=settings.source,
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
