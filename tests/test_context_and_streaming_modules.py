"""Coverage-focused tests for context and streaming modules."""

from __future__ import annotations

import importlib
from queue import Queue

from fastapi.responses import StreamingResponse


def test_context_modules_import_and_instantiation() -> None:
    contexts = importlib.import_module("tactix.sync_contexts")

    dummy_settings = object()
    dummy_fetch_context = object()
    dummy_progress = None
    dummy_game_rows: list[object] = []

    contexts.DailySyncPayloadContext(
        settings=dummy_settings,
        fetch_context=dummy_fetch_context,
        games=dummy_game_rows,
        raw_pgns_inserted=0,
        raw_pgns_hashed=0,
        raw_pgns_matched=0,
        postgres_raw_pgns_inserted=0,
        positions_count=0,
        tactics_count=0,
        metrics_version=0,
        checkpoint_value=None,
        last_timestamp_value=0,
        backfill_mode=False,
    )

    contexts.FetchProgressContext(
        settings=dummy_settings,
        progress=dummy_progress,
        fetch_context=dummy_fetch_context,
        backfill_mode=False,
        window_start_ms=None,
        window_end_ms=None,
        fetched_games=0,
    )

    contexts.DailySyncStartContext(
        settings=dummy_settings,
        progress=dummy_progress,
        profile=None,
        backfill_mode=False,
        window_start_ms=None,
        window_end_ms=None,
    )
    contexts.DailyGameSyncContext(
        settings=dummy_settings,
        client=object(),
        progress=dummy_progress,
        window_start_ms=None,
        window_end_ms=None,
        profile=None,
    )
    contexts.DailyGameSyncRequest()
    contexts.PrepareGamesForSyncContext(
        settings=dummy_settings,
        client=object(),
        backfill_mode=False,
        window_start_ms=None,
        window_end_ms=None,
        progress=dummy_progress,
    )
    contexts.WindowFilterContext(
        settings=dummy_settings,
        progress=dummy_progress,
        backfill_mode=False,
        window_filtered=0,
        window_start_ms=None,
        window_end_ms=None,
    )
    contexts.FetchProgressContext(
        settings=dummy_settings,
        progress=dummy_progress,
        fetch_context=dummy_fetch_context,
        backfill_mode=False,
        window_start_ms=None,
        window_end_ms=None,
        fetched_games=0,
    )
    contexts.DailySyncCompleteContext(
        settings=dummy_settings,
        profile=None,
        games=dummy_game_rows,
        raw_pgns_inserted=0,
        postgres_raw_pgns_inserted=0,
        positions_count=0,
        tactics_count=0,
        postgres_written=0,
        postgres_synced=0,
        metrics_version=0,
        backfill_mode=False,
    )
    contexts.NoGamesPayloadContext(
        settings=dummy_settings,
        conn=object(),
        backfill_mode=False,
        fetch_context=dummy_fetch_context,
        last_timestamp_value=0,
        window_filtered=0,
    )
    contexts.NoGamesAfterDedupePayloadContext(
        settings=dummy_settings,
        conn=object(),
        backfill_mode=False,
        fetch_context=dummy_fetch_context,
        last_timestamp_value=0,
        games=dummy_game_rows,
        window_filtered=0,
    )
    contexts.NoGamesContext(
        settings=dummy_settings,
        conn=object(),
        progress=dummy_progress,
        backfill_mode=False,
        fetch_context=dummy_fetch_context,
        last_timestamp_value=0,
        window_filtered=0,
    )
    contexts.NoGamesAfterDedupeContext(
        settings=dummy_settings,
        conn=object(),
        progress=dummy_progress,
        backfill_mode=False,
        fetch_context=dummy_fetch_context,
        last_timestamp_value=0,
        games=dummy_game_rows,
        window_filtered=0,
    )


def test_stream_jobs_api_returns_streaming_response(monkeypatch) -> None:
    stream_jobs_api = importlib.import_module("tactix.job_stream")

    def fake_stream_job_response(request, settings_factory):
        assert request.job == "daily_game_sync"
        assert settings_factory() == "settings"
        return StreamingResponse(iter(()))

    monkeypatch.setattr(stream_jobs_api, "_stream_job_response", fake_stream_job_response)
    monkeypatch.setattr(stream_jobs_api, "get_settings", lambda: "settings")

    response = stream_jobs_api.stream_jobs()
    assert isinstance(response, StreamingResponse)


def test_apply_engine_options_exec(monkeypatch) -> None:
    apply_engine_options = importlib.import_module("tactix._apply_engine_options")

    engine = object()
    options = {"Threads": 2}

    def fake_filter_supported_options(engine_arg, options_arg):
        assert engine_arg is engine
        assert options_arg is options
        return {"Threads": 2}

    def fake_configure_engine_options(engine_arg, options_arg):
        assert engine_arg is engine
        assert options_arg == {"Threads": 2}
        return {"applied": True}

    monkeypatch.setattr(
        apply_engine_options, "_filter_supported_options", fake_filter_supported_options
    )
    monkeypatch.setattr(
        apply_engine_options, "_configure_engine_options", fake_configure_engine_options
    )

    assert apply_engine_options._apply_engine_options(engine, options) == {"applied": True}


def test_streaming_response_job_stream(monkeypatch) -> None:
    streaming_module = importlib.import_module("tactix.job_stream")

    def fake_event_stream(queue, sentinel):
        assert queue is not None
        assert sentinel is not None
        return iter([b"data: ok\n\n"])

    monkeypatch.setattr(streaming_module, "_event_stream", fake_event_stream)

    response = streaming_module._streaming_response(Queue(), object())
    assert isinstance(response, StreamingResponse)
