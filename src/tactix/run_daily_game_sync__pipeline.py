"""Run the daily game sync pipeline with resolved settings."""

from __future__ import annotations

from typing import cast

from tactix.build_chess_client__pipeline import _build_chess_client
from tactix.build_pipeline_settings__pipeline import _build_pipeline_settings
from tactix.config import Settings
from tactix.DailySyncStartContext import DailyGameSyncContext, DailyGameSyncRequest
from tactix.legacy_args import apply_legacy_args, apply_legacy_kwargs, init_legacy_values
from tactix.pipeline_state__pipeline import ProgressCallback
from tactix.ports.game_source_client import GameSourceClient
from tactix.run_daily_game_sync_internal__pipeline import _run_daily_game_sync


def run_daily_game_sync(
    request: DailyGameSyncRequest | Settings,
    *args: object,
    **legacy: object,
) -> dict[str, object]:
    """Execute the daily game sync pipeline for a request."""
    if isinstance(request, DailyGameSyncRequest):
        resolved = request
    else:
        ordered_keys = (
            "source",
            "progress",
            "profile",
            "window_start_ms",
            "window_end_ms",
            "client",
        )
        values = init_legacy_values(ordered_keys)
        apply_legacy_kwargs(values, ordered_keys, legacy)
        apply_legacy_args(values, ordered_keys, args)
        resolved = DailyGameSyncRequest(
            settings=request,
            source=cast(str | None, values["source"]),
            progress=cast(ProgressCallback | None, values["progress"]),
            profile=cast(str | None, values["profile"]),
            window_start_ms=cast(int | None, values["window_start_ms"]),
            window_end_ms=cast(int | None, values["window_end_ms"]),
            client=cast(GameSourceClient | None, values["client"]),
        )
    settings = _build_pipeline_settings(
        resolved.settings,
        source=resolved.source,
        profile=resolved.profile,
    )
    client = _build_chess_client(settings, resolved.client)
    return _run_daily_game_sync(
        DailyGameSyncContext(
            settings=settings,
            client=client,
            progress=resolved.progress,
            window_start_ms=resolved.window_start_ms,
            window_end_ms=resolved.window_end_ms,
            profile=resolved.profile,
        )
    )
