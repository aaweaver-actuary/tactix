from __future__ import annotations

from tactix.DailySyncStartContext import NoGamesPayloadContext
from tactix.no_games_checkpoint__pipeline import _no_games_checkpoint
from tactix.no_games_cursor__pipeline import _no_games_cursor
from tactix.update_metrics_and_version__pipeline import _update_metrics_and_version


def _build_no_games_payload(
    ctx: NoGamesPayloadContext,
) -> dict[str, object]:
    metrics_version = _update_metrics_and_version(ctx.settings, ctx.conn)
    checkpoint_ms = _no_games_checkpoint(
        ctx.settings,
        ctx.backfill_mode,
        ctx.fetch_context,
    )
    cursor = _no_games_cursor(ctx.backfill_mode, ctx.fetch_context)
    return {
        "source": ctx.settings.source,
        "user": ctx.settings.user,
        "fetched_games": 0,
        "raw_pgns_inserted": 0,
        "raw_pgns_hashed": 0,
        "raw_pgns_matched": 0,
        "positions": 0,
        "tactics": 0,
        "metrics_version": metrics_version,
        "checkpoint_ms": checkpoint_ms,
        "cursor": cursor,
        "last_timestamp_ms": ctx.last_timestamp_value or ctx.fetch_context.since_ms,
        "since_ms": ctx.fetch_context.since_ms,
        "window_filtered": ctx.window_filtered,
    }
