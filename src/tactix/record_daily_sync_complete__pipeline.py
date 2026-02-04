from __future__ import annotations

from tactix.DailySyncCompleteContext import DailySyncCompleteContext
from tactix.ops_event import OpsEvent
from tactix.record_ops_event import record_ops_event


def _record_daily_sync_complete(
    context: DailySyncCompleteContext,
) -> None:
    record_ops_event(
        OpsEvent(
            settings=context.settings,
            component=context.settings.run_context,
            event_type="daily_game_sync_complete",
            source=context.settings.source,
            profile=context.profile,
            metadata={
                "fetched_games": len(context.games),
                "raw_pgns_inserted": context.raw_pgns_inserted,
                "postgres_raw_pgns_inserted": context.postgres_raw_pgns_inserted,
                "positions": context.positions_count,
                "tactics": context.tactics_count,
                "postgres_tactics_written": context.postgres_written,
                "postgres_tactics_synced": context.postgres_synced,
                "metrics_version": context.metrics_version,
                "backfill": context.backfill_mode,
            },
        )
    )
