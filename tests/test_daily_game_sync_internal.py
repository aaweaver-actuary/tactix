from __future__ import annotations

from unittest.mock import MagicMock

from tactix.FetchContext import FetchContext
from tactix.config import Settings
from tactix.run_daily_game_sync_internal__pipeline import _run_daily_game_sync
from tactix.sync_contexts import DailyGameSyncContext


def test_run_daily_game_sync_handles_no_games_after_dedupe(monkeypatch, tmp_path) -> None:
    settings = Settings(source="lichess", duckdb_path=tmp_path / "db.duckdb")
    context = DailyGameSyncContext(
        settings=settings,
        client=MagicMock(),
        progress=None,
        window_start_ms=None,
        window_end_ms=None,
        profile=None,
    )
    games = [{"game_id": "g1", "last_timestamp_ms": 10}]
    fetch_context = FetchContext(raw_games=[], since_ms=0)

    monkeypatch.setattr(
        "tactix.run_daily_game_sync_internal__pipeline.get_connection",
        lambda _path: object(),
    )
    monkeypatch.setattr(
        "tactix.run_daily_game_sync_internal__pipeline.init_schema",
        lambda _conn: None,
    )
    monkeypatch.setattr(
        "tactix.run_daily_game_sync_internal__pipeline._emit_daily_sync_start",
        lambda _ctx: None,
    )
    monkeypatch.setattr(
        "tactix.run_daily_game_sync_internal__pipeline._prepare_games_for_sync",
        lambda _ctx: (games, fetch_context, 0, 10),
    )
    monkeypatch.setattr(
        "tactix.run_daily_game_sync_internal__pipeline._apply_backfill_filter",
        lambda *_args, **_kwargs: ([], games),
    )

    sentinel = {"result": "no-games-after-dedupe"}
    monkeypatch.setattr(
        "tactix.run_daily_game_sync_internal__pipeline._handle_no_games_after_dedupe",
        lambda _ctx: sentinel,
    )

    assert _run_daily_game_sync(context) == sentinel
