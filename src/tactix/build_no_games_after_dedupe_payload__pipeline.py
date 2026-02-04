"""Build payload when no games remain after dedupe."""

from __future__ import annotations

from tactix.apply_no_games_dedupe_checkpoint__pipeline import _apply_no_games_dedupe_checkpoint
from tactix.DailySyncStartContext import NoGamesAfterDedupePayloadContext
from tactix.no_games_cursor__pipeline import _no_games_cursor
from tactix.update_metrics_and_version__pipeline import _update_metrics_and_version


def _build_no_games_after_dedupe_payload(
    ctx: NoGamesAfterDedupePayloadContext,
) -> dict[str, object]:
    metrics_version = _update_metrics_and_version(ctx.settings, ctx.conn)
    checkpoint_ms, last_timestamp_value = _apply_no_games_dedupe_checkpoint(
        ctx.settings,
        ctx.backfill_mode,
        ctx.fetch_context,
        ctx.last_timestamp_value,
    )
    return {
        "source": ctx.settings.source,
        "user": ctx.settings.user,
        "fetched_games": len(ctx.games),
        "raw_pgns_inserted": 0,
        "raw_pgns_hashed": 0,
        "raw_pgns_matched": 0,
        "postgres_raw_pgns_inserted": 0,
        "positions": 0,
        "tactics": 0,
        "metrics_version": metrics_version,
        "checkpoint_ms": checkpoint_ms,
        "cursor": _no_games_cursor(ctx.backfill_mode, ctx.fetch_context),
        "last_timestamp_ms": last_timestamp_value,
        "since_ms": ctx.fetch_context.since_ms,
        "window_filtered": ctx.window_filtered,
    }
