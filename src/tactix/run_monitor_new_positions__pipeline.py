from __future__ import annotations

from tactix.analyze_positions__pipeline import _analyze_positions
from tactix.collect_positions_for_monitor__pipeline import _collect_positions_for_monitor
from tactix.config import Settings
from tactix.pipeline_state__pipeline import logger
from tactix.postgres_store import record_ops_event
from tactix.prepare_raw_pgn_context__pipeline import _prepare_raw_pgn_context
from tactix.update_metrics_and_version__pipeline import _update_metrics_and_version


def run_monitor_new_positions(
    settings: Settings | None = None,
    source: str | None = None,
    profile: str | None = None,
    limit: int | None = None,
) -> dict[str, object]:
    settings, conn, raw_pgns = _prepare_raw_pgn_context(
        settings=settings,
        source=source,
        profile=profile,
        limit=limit,
    )
    positions_extracted, new_game_ids, positions_to_analyze = _collect_positions_for_monitor(
        conn, settings, raw_pgns
    )

    positions_analyzed, tactics_detected = _analyze_positions(conn, settings, positions_to_analyze)

    metrics_version = _update_metrics_and_version(settings, conn)

    logger.info(
        "Monitor run complete: source=%s new_games=%s positions_extracted=%s "
        "positions_analyzed=%s tactics_detected=%s metrics_version=%s",
        settings.source,
        len(new_game_ids),
        positions_extracted,
        positions_analyzed,
        tactics_detected,
        metrics_version,
    )

    record_ops_event(
        settings,
        component=settings.run_context,
        event_type="monitor_new_positions_complete",
        source=settings.source,
        profile=profile,
        metadata={
            "new_games": len(new_game_ids),
            "positions_extracted": positions_extracted,
            "positions_analyzed": positions_analyzed,
            "tactics_detected": tactics_detected,
            "metrics_version": metrics_version,
        },
    )

    return {
        "source": settings.source,
        "user": settings.user,
        "raw_pgns_checked": len(raw_pgns),
        "new_games": len(new_game_ids),
        "positions_extracted": positions_extracted,
        "positions_analyzed": positions_analyzed,
        "tactics_detected": tactics_detected,
        "metrics_version": metrics_version,
    }
