from __future__ import annotations

from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import FetchContext, GameRow


def _build_daily_sync_payload(
    settings: Settings,
    fetch_context: FetchContext,
    games: list[GameRow],
    raw_pgns_inserted: int,
    raw_pgns_hashed: int,
    raw_pgns_matched: int,
    postgres_raw_pgns_inserted: int,
    positions_count: int,
    tactics_count: int,
    metrics_version: int,
    checkpoint_value: int | None,
    last_timestamp_value: int,
    backfill_mode: bool,
) -> dict[str, object]:
    return {
        "source": settings.source,
        "user": settings.user,
        "fetched_games": len(games),
        "raw_pgns_inserted": raw_pgns_inserted,
        "raw_pgns_hashed": raw_pgns_hashed,
        "raw_pgns_matched": raw_pgns_matched,
        "postgres_raw_pgns_inserted": postgres_raw_pgns_inserted,
        "positions": positions_count,
        "tactics": tactics_count,
        "metrics_version": metrics_version,
        "checkpoint_ms": checkpoint_value,
        "cursor": fetch_context.cursor_before
        if backfill_mode
        else (fetch_context.next_cursor or fetch_context.cursor_value),
        "last_timestamp_ms": last_timestamp_value,
        "since_ms": fetch_context.since_ms,
    }
