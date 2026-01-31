from __future__ import annotations

from tactix.build_no_games_payload__pipeline import _build_no_games_payload
from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import FetchContext, ProgressCallback, logger
from tactix.emit_progress__pipeline import _emit_progress


def _handle_no_games(
    settings: Settings,
    conn,
    progress: ProgressCallback | None,
    backfill_mode: bool,
    fetch_context: FetchContext,
    last_timestamp_value: int,
    window_filtered: int,
) -> dict[str, object]:
    logger.info(
        "No new games for source=%s at checkpoint=%s",
        settings.source,
        fetch_context.since_ms,
    )
    _emit_progress(
        progress,
        "no_games",
        source=settings.source,
        message="No new games to process",
    )
    return _build_no_games_payload(
        settings,
        conn,
        backfill_mode,
        fetch_context,
        last_timestamp_value,
        window_filtered,
    )
