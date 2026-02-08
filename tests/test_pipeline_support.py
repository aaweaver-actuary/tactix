from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tactix.app.use_cases import pipeline_support as pipeline_support_module
from tactix.app.use_cases.pipeline_support import (
    PipelineAnalysisCheckpoint,
    PipelineCheckpointUpdates,
    PipelineCoercions,
    PipelineEmissions,
    PipelineNoGames,
    PipelineProfileFilters,
)
from tactix.chess_clients.chess_fetch_result import ChessFetchResult
from tactix.config import Settings
from tactix.sync_contexts import (
    DailySyncStartContext,
    FetchProgressContext,
    NoGamesAfterDedupeContext,
    NoGamesAfterDedupePayloadContext,
    NoGamesContext,
    NoGamesPayloadContext,
    WindowFilterContext,
)
from tactix.FetchContext import FetchContext
from tactix.GameRow import GameRow
from tactix.define_pipeline_state__pipeline import (
    CHESSCOM_BLACK_PROFILES,
    LICHESS_BLACK_PROFILES,
)


class FakeCheckpointWriter:
    """Test double for checkpoint persistence."""

    def write_chesscom_cursor(self, path, cursor: str | None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("" if cursor is None else cursor)

    def write_lichess_checkpoint(self, path, since_ms: int) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(since_ms))


def _sample_game(last_timestamp_ms: int) -> GameRow:
    return {
        "game_id": "game-1",
        "user": "lichess",
        "source": "lichess",
        "fetched_at": datetime.now(UTC),
        "pgn": "",
        "last_timestamp_ms": last_timestamp_ms,
    }


def test_pipeline_coercions() -> None:
    coercions = PipelineCoercions()

    assert coercions.coerce_int(True) == 1
    assert coercions.coerce_int(2.9) == 2
    assert coercions.coerce_int("bad") == 0
    assert coercions.coerce_int({}) == 0

    assert coercions.coerce_str(None) == ""
    assert coercions.coerce_str("ok") == "ok"
    assert coercions.coerce_str(123) == "123"

    assert coercions.coerce_pgn(b"1. e4") == "1. e4"
    assert coercions.coerce_pgn("1. d4") == "1. d4"


def test_pipeline_profile_filters() -> None:
    filters = PipelineProfileFilters()

    assert filters.black_profiles_for_source("lichess") == LICHESS_BLACK_PROFILES
    assert filters.black_profiles_for_source("chesscom") == CHESSCOM_BLACK_PROFILES
    assert filters.black_profiles_for_source("unknown") is None

    settings = Settings(source="lichess")
    settings.lichess_profile = " Blitz "
    assert filters.normalized_profile_for_source(settings, "lichess") == "blitz"

    chesscom_settings = Settings(source="chesscom")
    chesscom_settings.chesscom_profile = "Rapid"
    assert filters.normalized_profile_for_source(chesscom_settings, "chesscom") == "rapid"

    assert filters.side_filter_for_profile("bullet", {"bullet"}) == "black"
    assert filters.side_filter_for_profile("rapid", {"bullet"}) is None

    if not LICHESS_BLACK_PROFILES:
        pytest.skip("No blacklisted lichess profiles configured")
    settings.lichess_profile = next(iter(LICHESS_BLACK_PROFILES))
    assert filters.resolve_side_to_move_filter(settings) == "black"


def test_pipeline_emissions(monkeypatch: pytest.MonkeyPatch) -> None:
    emissions = PipelineEmissions()
    payloads: list[dict[str, object]] = []

    def progress(payload: dict[str, object]) -> None:
        payloads.append(payload)

    emissions.emit_progress(progress, "step", value=1)
    assert payloads[0]["step"] == "step"
    assert payloads[0]["value"] == 1
    assert isinstance(payloads[0]["timestamp"], float)

    settings = Settings(source="lichess")
    fetch_context = FetchContext(
        raw_games=[],
        since_ms=10,
        cursor_before="prev",
        cursor_value="c1",
        next_cursor="c2",
    )
    emissions.emit_fetch_progress(
        FetchProgressContext(
            settings=settings,
            progress=progress,
            fetch_context=fetch_context,
            backfill_mode=False,
            window_start_ms=None,
            window_end_ms=None,
            fetched_games=2,
        )
    )
    assert payloads[-1]["step"] == "fetch_games"

    emissions.emit_positions_ready(settings, progress, [{"position_id": 1}])
    assert payloads[-1]["step"] == "positions_ready"

    start_count = len(payloads)
    emissions.emit_backfill_window_filtered(settings, progress, 0, None, None)
    assert len(payloads) == start_count
    emissions.emit_backfill_window_filtered(settings, progress, 2, 1, 2)
    assert payloads[-1]["step"] == "backfill_window_filtered"

    emissions.maybe_emit_analysis_progress(
        progress, settings, idx=2, total_positions=3, progress_every=10
    )
    assert payloads[-1]["step"] == "analyze_positions"

    emissions.maybe_emit_window_filtered(
        WindowFilterContext(
            settings=settings,
            progress=progress,
            backfill_mode=True,
            window_filtered=1,
            window_start_ms=1,
            window_end_ms=2,
        )
    )
    assert payloads[-1]["step"] == "backfill_window_filtered"

    captured: list[object] = []

    def fake_record(event: object) -> bool:
        captured.append(event)
        return True

    monkeypatch.setattr(pipeline_support_module, "record_ops_event", fake_record)

    emissions.emit_daily_sync_start(
        DailySyncStartContext(
            settings=settings,
            progress=progress,
            profile="rapid",
            backfill_mode=False,
            window_start_ms=None,
            window_end_ms=None,
        )
    )
    assert captured


def test_pipeline_no_games(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    no_games = PipelineNoGames(checkpoint_writer=FakeCheckpointWriter())
    settings = Settings(source="lichess")
    settings.checkpoint_path = tmp_path / "checkpoint.txt"

    fetch_context = FetchContext(
        raw_games=[],
        since_ms=10,
        cursor_before="before",
        cursor_value="cur",
        next_cursor="next",
    )

    assert no_games.no_games_checkpoint(settings, False, fetch_context) == 10
    assert no_games.no_games_checkpoint(settings, True, fetch_context) is None

    chesscom_settings = Settings(source="chesscom")
    chesscom_settings.checkpoint_path = tmp_path / "cursor.txt"
    assert no_games.no_games_checkpoint(chesscom_settings, False, fetch_context) is None

    assert no_games.no_games_cursor(True, fetch_context) == "before"
    assert no_games.no_games_cursor(False, fetch_context) == "next"

    checkpoint_value, last_timestamp = no_games.apply_no_games_dedupe_checkpoint(
        settings,
        backfill_mode=False,
        fetch_context=fetch_context,
        last_timestamp_value=15,
    )
    assert checkpoint_value == 15
    assert last_timestamp == 15
    assert settings.checkpoint_path.read_text() == "15"

    chesscom_checkpoint, chesscom_last = no_games.apply_no_games_dedupe_checkpoint(
        chesscom_settings,
        backfill_mode=False,
        fetch_context=fetch_context,
        last_timestamp_value=20,
    )
    assert chesscom_checkpoint is None
    assert chesscom_last == 20
    assert chesscom_settings.checkpoint_path.read_text() == "next"

    monkeypatch.setattr(pipeline_support_module, "_update_metrics_and_version", lambda *_: 7)

    payload = no_games.build_no_games_payload(
        NoGamesPayloadContext(
            settings=settings,
            conn=object(),
            backfill_mode=False,
            fetch_context=fetch_context,
            last_timestamp_value=15,
            window_filtered=0,
        )
    )
    assert payload["metrics_version"] == 7
    assert payload["checkpoint_ms"] == 10
    assert payload["cursor"] == "next"

    payload_after_dedupe = no_games.build_no_games_after_dedupe_payload(
        NoGamesAfterDedupePayloadContext(
            settings=settings,
            conn=object(),
            backfill_mode=False,
            games=[_sample_game(15)],
            fetch_context=fetch_context,
            last_timestamp_value=15,
            window_filtered=0,
        )
    )
    assert payload_after_dedupe["fetched_games"] == 1
    assert payload_after_dedupe["metrics_version"] == 7

    progress_payloads: list[dict[str, object]] = []

    def progress(payload: dict[str, object]) -> None:
        progress_payloads.append(payload)

    handled = no_games.handle_no_games(
        NoGamesContext(
            settings=settings,
            conn=object(),
            progress=progress,
            backfill_mode=False,
            fetch_context=fetch_context,
            last_timestamp_value=15,
            window_filtered=0,
        )
    )
    assert handled["metrics_version"] == 7
    assert progress_payloads[-1]["step"] == "no_games"

    handled_after_dedupe = no_games.handle_no_games_after_dedupe(
        NoGamesAfterDedupeContext(
            settings=settings,
            conn=object(),
            progress=progress,
            backfill_mode=False,
            games=[_sample_game(15)],
            fetch_context=fetch_context,
            last_timestamp_value=15,
            window_filtered=0,
        )
    )
    assert handled_after_dedupe["fetched_games"] == 1


def test_pipeline_analysis_checkpoint(tmp_path) -> None:
    checkpoints = PipelineAnalysisCheckpoint()
    checkpoint_path = tmp_path / "analysis.json"

    assert checkpoints.read_analysis_checkpoint(checkpoint_path, "sig") == -1

    checkpoints.write_analysis_checkpoint(checkpoint_path, "sig", 3)
    assert checkpoints.read_analysis_checkpoint(checkpoint_path, "sig") == 3
    assert checkpoints.read_analysis_checkpoint(checkpoint_path, "other") == -1

    checkpoints.maybe_write_analysis_checkpoint(None, "sig", 5)
    checkpoints.maybe_clear_analysis_checkpoint(None)

    checkpoints.clear_analysis_checkpoint(checkpoint_path)
    assert not checkpoint_path.exists()


def test_pipeline_checkpoint_updates(tmp_path) -> None:
    updates = PipelineCheckpointUpdates(checkpoint_writer=FakeCheckpointWriter())

    assert updates.cursor_last_timestamp(None) == 0
    assert updates.cursor_last_timestamp("123:cursor") == 123
    assert updates.cursor_last_timestamp("bad") == 0

    games = [_sample_game(10), _sample_game(20)]
    assert updates.resolve_last_timestamp_value(games, 5) == 20
    assert updates.resolve_last_timestamp_value([], 5) == 5

    fetch_context = FetchContext(raw_games=[], since_ms=0, chesscom_result=ChessFetchResult())
    fetch_context.chesscom_result.last_timestamp_ms = 99
    assert updates.resolve_chesscom_last_timestamp(fetch_context, [], 10) == 99

    settings = Settings(source="lichess")
    settings.checkpoint_path = tmp_path / "lichess.txt"
    lichess_result = updates.update_lichess_checkpoint(
        settings,
        FetchContext(raw_games=[], since_ms=10),
        [_sample_game(20)],
    )
    assert lichess_result == (20, 20)
    assert settings.checkpoint_path.read_text() == "20"

    chesscom_settings = Settings(source="chesscom")
    chesscom_settings.checkpoint_path = tmp_path / "chesscom.txt"
    chesscom_result = updates.update_chesscom_checkpoint(
        chesscom_settings,
        FetchContext(raw_games=[], since_ms=0, next_cursor="cursor"),
        [],
        7,
    )
    assert chesscom_result == (None, 7)
    assert chesscom_settings.checkpoint_path.read_text() == "cursor"

    daily_result = updates.update_daily_checkpoint(
        chesscom_settings,
        backfill_mode=True,
        fetch_context=FetchContext(raw_games=[], since_ms=0),
        games=[],
        last_timestamp_value=11,
    )
    assert daily_result == (None, 11)
