from __future__ import annotations

from tactix.config import Settings
from tactix.pipeline_state__pipeline import GameRow
from tactix.record_ops_event import record_ops_event


def _record_daily_sync_complete(
    settings: Settings,
    profile: str | None,
    games: list[GameRow],
    raw_pgns_inserted: int,
    postgres_raw_pgns_inserted: int,
    positions_count: int,
    tactics_count: int,
    postgres_written: int,
    postgres_synced: int,
    metrics_version: int,
    backfill_mode: bool,
) -> None:
    record_ops_event(
        settings,
        component=settings.run_context,
        event_type="daily_game_sync_complete",
        source=settings.source,
        profile=profile,
        metadata={
            "fetched_games": len(games),
            "raw_pgns_inserted": raw_pgns_inserted,
            "postgres_raw_pgns_inserted": postgres_raw_pgns_inserted,
            "positions": positions_count,
            "tactics": tactics_count,
            "postgres_tactics_written": postgres_written,
            "postgres_tactics_synced": postgres_synced,
            "metrics_version": metrics_version,
            "backfill": backfill_mode,
        },
    )
