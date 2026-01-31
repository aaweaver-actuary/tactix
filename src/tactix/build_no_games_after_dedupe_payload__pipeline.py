from __future__ import annotations

from tactix.apply_no_games_dedupe_checkpoint__pipeline import _apply_no_games_dedupe_checkpoint
from tactix.config import Settings
from tactix.no_games_cursor__pipeline import _no_games_cursor
from tactix.pipeline_state__pipeline import FetchContext, GameRow
from tactix.update_metrics_and_version__pipeline import _update_metrics_and_version


def _build_no_games_after_dedupe_payload(
    settings: Settings,
    conn,
    backfill_mode: bool,
    fetch_context: FetchContext,
    last_timestamp_value: int,
    games: list[GameRow],
    window_filtered: int,
) -> dict[str, object]:
    metrics_version = _update_metrics_and_version(settings, conn)
    checkpoint_ms, last_timestamp_value = _apply_no_games_dedupe_checkpoint(
        settings,
        backfill_mode,
        fetch_context,
        last_timestamp_value,
    )
    return {
        "source": settings.source,
        "user": settings.user,
        "fetched_games": len(games),
        "raw_pgns_inserted": 0,
        "raw_pgns_hashed": 0,
        "raw_pgns_matched": 0,
        "postgres_raw_pgns_inserted": 0,
        "positions": 0,
        "tactics": 0,
        "metrics_version": metrics_version,
        "checkpoint_ms": checkpoint_ms,
        "cursor": _no_games_cursor(backfill_mode, fetch_context),
        "last_timestamp_ms": last_timestamp_value,
        "since_ms": fetch_context.since_ms,
        "window_filtered": window_filtered,
    }
