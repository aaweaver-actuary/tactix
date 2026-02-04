"""Build the daily sync payload for API responses."""

from __future__ import annotations

from tactix.DailySyncStartContext import DailySyncPayloadContext


def _build_daily_sync_payload(
    ctx: DailySyncPayloadContext,
) -> dict[str, object]:
    """Return a JSON payload summarizing daily sync results."""
    return {
        "source": ctx.settings.source,
        "user": ctx.settings.user,
        "fetched_games": len(ctx.games),
        "raw_pgns_inserted": ctx.raw_pgns_inserted,
        "raw_pgns_hashed": ctx.raw_pgns_hashed,
        "raw_pgns_matched": ctx.raw_pgns_matched,
        "postgres_raw_pgns_inserted": ctx.postgres_raw_pgns_inserted,
        "positions": ctx.positions_count,
        "tactics": ctx.tactics_count,
        "metrics_version": ctx.metrics_version,
        "checkpoint_ms": ctx.checkpoint_value,
        "cursor": ctx.fetch_context.cursor_before
        if ctx.backfill_mode
        else (ctx.fetch_context.next_cursor or ctx.fetch_context.cursor_value),
        "last_timestamp_ms": ctx.last_timestamp_value,
        "since_ms": ctx.fetch_context.since_ms,
    }
