from unittest.mock import MagicMock, patch

from tactix.trigger_daily_sync__api_jobs import trigger_daily_sync


def test_trigger_daily_sync_runs_pipeline_and_refreshes_cache() -> None:
    settings = MagicMock()
    with (
        patch(
            "tactix.trigger_daily_sync__api_jobs.get_settings", return_value=settings
        ) as get_settings,
        patch(
            "tactix.trigger_daily_sync__api_jobs.run_daily_game_sync",
            return_value={"games": 1},
        ) as run_daily_game_sync,
        patch(
            "tactix.trigger_daily_sync__api_jobs._refresh_dashboard_cache_async",
        ) as refresh_cache,
        patch(
            "tactix.trigger_daily_sync__api_jobs._sources_for_cache_refresh",
            return_value=["chesscom"],
        ) as sources_for_cache,
    ):
        result = trigger_daily_sync(
            source="chesscom",
            backfill_start_ms=10,
            backfill_end_ms=20,
            profile="blitz",
        )

    get_settings.assert_called_once_with(source="chesscom", profile="blitz")
    run_daily_game_sync.assert_called_once_with(
        settings,
        source="chesscom",
        window_start_ms=10,
        window_end_ms=20,
        profile="blitz",
    )
    sources_for_cache.assert_called_once_with("chesscom")
    refresh_cache.assert_called_once_with(["chesscom"])
    assert result == {"status": "ok", "result": {"games": 1}}
