from __future__ import annotations

from tactix.build_chess_client__pipeline import _build_chess_client
from tactix.build_pipeline_settings__pipeline import _build_pipeline_settings
from tactix.chess_clients.base_chess_client import BaseChessClient
from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import ProgressCallback
from tactix.run_daily_game_sync_internal__pipeline import _run_daily_game_sync


def run_daily_game_sync(
    settings: Settings | None = None,
    source: str | None = None,
    progress: ProgressCallback | None = None,
    window_start_ms: int | None = None,
    window_end_ms: int | None = None,
    profile: str | None = None,
    client: BaseChessClient | None = None,
) -> dict[str, object]:
    settings = _build_pipeline_settings(settings, source=source, profile=profile)
    client = _build_chess_client(settings, client)
    return _run_daily_game_sync(
        settings,
        client,
        progress,
        window_start_ms,
        window_end_ms,
        profile,
    )
