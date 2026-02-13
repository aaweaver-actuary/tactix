from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime
from queue import Queue
from types import SimpleNamespace

import chess
import chess.pgn
import psycopg2
import pytest
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from tactix.airflow_daily_sync_context import AirflowDailySyncTriggerContext
from tactix.chess_game_result import ChessGameResult
from tactix.chess_player_color import ChessPlayerColor
from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import RESUME_INDEX_START
from tactix.domain.tactics_outcome import (
    _apply_int_threshold,
    _apply_unclear_args,
    _apply_unclear_threshold,
    resolve_unclear_outcome_context,
    should_override_failed_attempt,
)
from tactix.engine_result import EngineResult
from tactix.extract_last_timestamp_ms import (
    _parse_date_header_timestamp,
    _parse_utc_header_timestamp,
    extract_last_timestamp_ms,
)
from tactix.extract_positions__pgn import _call_rust_extractor
from tactix.extractor_context import ExtractorRequest
from tactix.extract_positions_for_new_games__pipeline import _extract_positions_for_new_games
from tactix.fetch_lichess_games__pipeline import _fetch_lichess_games
from tactix.get_job_status__api_jobs import get_job_status
from tactix.get_postgres_status import get_postgres_status
from tactix.job_stream import (
    MetricsFilters,
    MetricsStreamContext,
    _build_stream_job_context,
    _collect_stream_job_values,
    _queue_job_complete,
    _queue_job_error,
    _queue_job_event,
    _resolve_backfill_window,
    _stream_metrics_worker,
    build_stream_job_kwargs,
    build_stream_job_request,
    build_stream_job_request_from_values,
    stream_metrics,
)
from tactix.load_resume_positions__pipeline import _load_resume_context
from tactix.load_fixture_games import FixtureGamesRequest, load_fixture_games
from tactix.maybe_sync_analysis_results__pipeline import _maybe_sync_analysis_results
from tactix.maybe_upsert_postgres_analysis__pipeline import _maybe_upsert_postgres_analysis
from tactix.outcome_context import BaseOutcomeContext, OutcomeResultEnum
from tactix.persist_raw_pgns__pipeline import PersistRawPgnsContext, _persist_raw_pgns
from tactix.pgn_context_kwargs import (
    build_pgn_context_inputs_from_values,
    build_pgn_context_kwargs,
    build_pgn_context_kwargs_from_values,
)
from tactix.pgn_headers import PgnHeaders, _coerce_pgn_datetime, _parse_pgn_date_str
from tactix.prepare_dag_helpers__airflow import (
    _apply_triggered_end,
    _coerce_optional_int,
    _dag_run_conf,
    _resolve_backfill_from_interval,
    resolve_backfill_window,
    resolve_profile,
    to_epoch_ms,
)
from tactix.read_fork_severity_floor__config import _read_fork_severity_floor
from tactix.resolve_user_fields__pgn_headers import _resolve_user_fields__pgn_headers
from tactix.run_daily_game_sync__pipeline import run_daily_game_sync
from tactix.unclear_outcome_params import UnclearOutcomeParams
from tactix.init_analysis_schema_if_needed__pipeline import _init_analysis_schema_if_needed
from tactix.sync_contexts import DailyGameSyncRequest
from tactix.sync_postgres_analysis_results__pipeline import _sync_postgres_analysis_results
from tactix.trigger_airflow_daily_sync__airflow_jobs import _trigger_airflow_daily_sync
from tactix.upsert_postgres_raw_pgns_if_enabled__pipeline import (
    _upsert_postgres_raw_pgns_if_enabled,
)
from tactix.utils.hasher import Hasher
from tactix.utils.hasher import hash as hash_value
from tactix.utils.hasher import hash_file as hash_file_value
from tactix.utils.now import Now
from tactix.infra.clients.chesscom_client import _extract_candidate_href
from tactix.validate_raw_pgn_hashes__pipeline import _validate_raw_pgn_hashes


def test_now_helpers() -> None:
    assert isinstance(Now.as_datetime(), datetime)
    assert isinstance(Now.as_dt(), datetime)
    assert isinstance(Now.as_seconds(), float)
    assert isinstance(Now.as_seconds(as_int=True), int)
    assert isinstance(Now.as_milliseconds(), int)

    naive_dt = datetime(2024, 1, 1, 12, 0, 0)
    aware_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert Now.to_utc(naive_dt).tzinfo == UTC
    assert Now.to_utc(aware_dt).tzinfo == UTC

    class BadDateTime:
        tzinfo = UTC

        def astimezone(self, _tz):
            raise TypeError("bad")

    assert Now.to_utc(None) is None
    assert Now.to_utc(BadDateTime()) is None


def test_hash_helpers(tmp_path) -> None:
    assert Hasher.hash_string("abc") == hash_value("abc")
    assert Hasher.hash_bytes(b"abc") == hash_value(b"abc", is_bytes=True)

    data_path = tmp_path / "data.txt"
    data_path.write_text("content", encoding="utf-8")
    assert hash_file_value(str(data_path)) == Hasher.hash_file(str(data_path))

    with pytest.raises(TypeError):
        hash_value(b"abc")

    with pytest.raises(TypeError):
        hash_value("abc", is_bytes=True)


def test_read_fork_severity_floor_env(monkeypatch) -> None:
    monkeypatch.delenv("TACTIX_FORK_SEVERITY_FLOOR", raising=False)
    assert _read_fork_severity_floor() is None

    monkeypatch.setenv("TACTIX_FORK_SEVERITY_FLOOR", "1.5")
    assert _read_fork_severity_floor() == 1.5


def test_get_job_status(monkeypatch) -> None:
    settings = Settings()
    monkeypatch.setattr("tactix.get_job_status__api_jobs.get_settings", lambda **_: settings)
    monkeypatch.setattr("tactix.get_job_status__api_jobs._airflow_enabled", lambda _settings: True)
    monkeypatch.setattr("tactix.get_job_status__api_jobs._resolve_backfill_end_ms", lambda *_: 123)
    monkeypatch.setattr("tactix.get_job_status__api_jobs.time_module.time", lambda: 1.0)

    payload = get_job_status(
        "daily_game_sync",
        source="Lichess",
        profile="rapid",
        backfill_start_ms=10,
        backfill_end_ms=20,
    )
    assert payload["job"] == "daily_game_sync"
    assert payload["airflow_enabled"] is True
    assert payload["backfill_end_ms"] == 123
    assert payload["requested_at_ms"] == 1000

    with pytest.raises(HTTPException):
        get_job_status("unknown_job")


def test_get_postgres_status_disabled(monkeypatch) -> None:
    settings = Settings()
    monkeypatch.setattr("tactix.get_postgres_status.postgres_enabled", lambda _s: False)
    status = get_postgres_status(settings)
    assert status.status == "disabled"


def test_get_postgres_status_unreachable(monkeypatch) -> None:
    settings = Settings()
    monkeypatch.setattr("tactix.get_postgres_status.postgres_enabled", lambda _s: True)
    monkeypatch.setattr("tactix.get_postgres_status._connection_kwargs", lambda _s: {"host": "x"})
    monkeypatch.setattr(
        "tactix.get_postgres_status.psycopg2.connect",
        lambda **_: (_ for _ in ()).throw(Exception("fail")),
    )

    status = get_postgres_status(settings)
    assert status.status == "unreachable"
    assert status.enabled is True


def test_get_postgres_status_ok(monkeypatch) -> None:
    settings = Settings()

    class FakeConn:
        autocommit = False

        def close(self) -> None:
            return None

    monkeypatch.setattr("tactix.get_postgres_status.postgres_enabled", lambda _s: True)
    monkeypatch.setattr("tactix.get_postgres_status._connection_kwargs", lambda _s: {"host": "x"})
    monkeypatch.setattr("tactix.get_postgres_status.psycopg2.connect", lambda **_: FakeConn())
    monkeypatch.setattr("tactix.get_postgres_status.init_postgres_schema", lambda _c: None)
    monkeypatch.setattr("tactix.get_postgres_status._collect_tables", lambda *_: ["games"])
    monkeypatch.setattr("tactix.get_postgres_status._build_schema_label", lambda _s: "public")

    status = get_postgres_status(settings)
    assert status.status == "ok"
    assert status.tables == ["games"]
    assert status.schema == "public"


def test_get_postgres_status_missing_kwargs(monkeypatch) -> None:
    settings = Settings()
    monkeypatch.setattr("tactix.get_postgres_status.postgres_enabled", lambda _s: True)
    monkeypatch.setattr("tactix.get_postgres_status._connection_kwargs", lambda _s: {})

    status = get_postgres_status(settings)
    assert status.status == "disabled"


def test_extract_positions_for_new_games(monkeypatch) -> None:
    settings = Settings()

    monkeypatch.setattr(
        "tactix.extract_positions_for_new_games__pipeline._collect_game_ids",
        lambda _rows: [],
    )
    empty_positions, empty_ids = _extract_positions_for_new_games(None, settings, [])
    assert empty_positions == []
    assert empty_ids == []

    raw_rows = [{"game_id": "g1"}]
    monkeypatch.setattr(
        "tactix.extract_positions_for_new_games__pipeline._collect_game_ids",
        lambda _rows: ["g1"],
    )
    monkeypatch.setattr(
        "tactix.extract_positions_for_new_games__pipeline.fetch_position_counts",
        lambda *_: {"g1": 1},
    )
    monkeypatch.setattr(
        "tactix.extract_positions_for_new_games__pipeline._filter_unprocessed_games",
        lambda *_: [],
    )
    empty_positions, empty_ids = _extract_positions_for_new_games(None, settings, raw_rows)
    assert empty_positions == []
    assert empty_ids == []

    positions = [{"position_id": "p1"}, {"position_id": "p2"}]
    monkeypatch.setattr(
        "tactix.extract_positions_for_new_games__pipeline._filter_unprocessed_games",
        lambda *_: raw_rows,
    )
    monkeypatch.setattr(
        "tactix.extract_positions_for_new_games__pipeline._extract_positions_for_rows",
        lambda *_: positions,
    )
    monkeypatch.setattr(
        "tactix.extract_positions_for_new_games__pipeline.insert_positions",
        lambda *_: ["p1", "p2"],
    )
    attach_calls = []

    def _capture_attach(pos, ids):
        attach_calls.append((pos, ids))

    monkeypatch.setattr(
        "tactix.extract_positions_for_new_games__pipeline._attach_position_ids",
        _capture_attach,
    )

    resolved_positions, resolved_ids = _extract_positions_for_new_games(None, settings, raw_rows)
    assert resolved_positions == positions
    assert resolved_ids == ["g1"]
    assert attach_calls


def test_fetch_lichess_games_builds_cursor(monkeypatch) -> None:
    settings = Settings()

    monkeypatch.setattr("tactix.fetch_lichess_games__pipeline.read_checkpoint", lambda _p: None)
    monkeypatch.setattr(
        "tactix.fetch_lichess_games__pipeline.resolve_fetch_window",
        lambda *_: ("cursor-val", 100, 200),
    )
    monkeypatch.setattr(
        "tactix.fetch_lichess_games__pipeline.build_cursor",
        lambda ts, gid: f"cursor-{ts}-{gid}",
    )

    class DummyClient:
        def fetch_incremental_games(self, _request):
            return SimpleNamespace(
                games=[{"last_timestamp_ms": 50, "game_id": "g1"}],
                last_timestamp_ms=50,
                next_cursor=None,
            )

    context = _fetch_lichess_games(settings, DummyClient(), False, None, None)
    assert context.cursor_value == "cursor-val"
    assert context.next_cursor == "cursor-50-g1"


def test_load_resume_context(monkeypatch, tmp_path) -> None:
    missing_path = tmp_path / "missing.json"
    positions, resume_index, signature = _load_resume_context(None, missing_path, [], "lichess")
    assert positions == []
    assert resume_index == -1
    assert signature == ""

    empty_path = tmp_path / "empty.json"
    empty_path.write_text("{}", encoding="utf-8")
    clear_calls = []
    monkeypatch.setattr(
        "tactix.load_resume_positions__pipeline.fetch_positions_for_games",
        lambda *_: [],
    )
    monkeypatch.setattr(
        "tactix.load_resume_positions__pipeline._clear_analysis_checkpoint",
        lambda *_: clear_calls.append("cleared"),
    )
    positions, resume_index, signature = _load_resume_context(None, empty_path, ["g1"], "lichess")
    assert positions == []
    assert resume_index == -1
    assert signature == ""
    assert clear_calls

    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "tactix.load_resume_positions__pipeline.fetch_positions_for_games",
        lambda *_: [{"user_to_move": True}, {"user_to_move": False}],
    )
    monkeypatch.setattr(
        "tactix.load_resume_positions__pipeline._analysis_signature",
        lambda *_: "sig",
    )
    monkeypatch.setattr(
        "tactix.load_resume_positions__pipeline._read_analysis_checkpoint",
        lambda *_: RESUME_INDEX_START,
    )

    positions, resume_index, signature = _load_resume_context(
        None, checkpoint_path, ["g1"], "lichess"
    )
    assert resume_index == RESUME_INDEX_START
    assert signature == "sig"
    assert positions == [{"user_to_move": True}, {"user_to_move": False}]

    calls = []
    monkeypatch.setattr(
        "tactix.load_resume_positions__pipeline._read_analysis_checkpoint",
        lambda *_: -1,
    )
    monkeypatch.setattr(
        "tactix.load_resume_positions__pipeline._clear_analysis_checkpoint",
        lambda *_: calls.append("cleared"),
    )
    positions, resume_index, signature = _load_resume_context(
        None, checkpoint_path, ["g1"], "lichess"
    )
    assert positions == []
    assert resume_index == -1
    assert signature == "sig"
    assert calls


def test_maybe_upsert_postgres_analysis(monkeypatch) -> None:
    assert _maybe_upsert_postgres_analysis(None, True, {}, {}) is False
    assert _maybe_upsert_postgres_analysis(object(), False, {}, {}) is False

    calls = []

    def _capture(*_args, **_kwargs):
        calls.append("ok")

    monkeypatch.setattr(
        "tactix.maybe_upsert_postgres_analysis__pipeline.upsert_analysis_tactic_with_outcome",
        _capture,
    )
    assert _maybe_upsert_postgres_analysis(object(), True, {"a": 1}, {"b": 2}) is True
    assert calls

    def _fail(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "tactix.maybe_upsert_postgres_analysis__pipeline.upsert_analysis_tactic_with_outcome",
        _fail,
    )
    assert _maybe_upsert_postgres_analysis(object(), True, {}, {}) is False


def test_pgn_context_kwargs_builders() -> None:
    inputs = build_pgn_context_inputs_from_values("pgn", "user", "lichess")
    kwargs = build_pgn_context_kwargs(inputs=inputs)
    assert kwargs["pgn"] == "pgn"
    assert kwargs["user"] == "user"
    assert kwargs["source"] == "lichess"

    kwargs_from_values = build_pgn_context_kwargs_from_values("pgn2", "user2", "chesscom")
    assert kwargs_from_values["pgn"] == "pgn2"
    assert kwargs_from_values["source"] == "chesscom"

    legacy_kwargs = build_pgn_context_kwargs(
        "pgn3",
        "user3",
        "lichess",
        game_id="g1",
        side_to_move_filter="white",
    )
    assert legacy_kwargs["game_id"] == "g1"
    assert legacy_kwargs["side_to_move_filter"] == "white"

    default_kwargs = build_pgn_context_kwargs()
    assert default_kwargs["pgn"] is None


def test_resolve_user_fields(monkeypatch) -> None:
    headers = chess.pgn.Headers()
    metadata = {"black_elo": 1500, "white_elo": 1600}

    monkeypatch.setattr(
        "tactix.resolve_user_fields__pgn_headers._get_user_color_from_pgn_headers",
        lambda *_: ChessPlayerColor.WHITE,
    )
    monkeypatch.setattr(
        "tactix.resolve_user_fields__pgn_headers._get_game_result_for_user_from_pgn_headers",
        lambda *_: ChessGameResult.WIN,
    )

    color, opp_rating, result = _resolve_user_fields__pgn_headers(headers, metadata, "user")
    assert color == "white"
    assert opp_rating == 1500
    assert result == ChessGameResult.WIN.value

    def _raise(*_args, **_kwargs):
        raise ValueError("bad")

    monkeypatch.setattr(
        "tactix.resolve_user_fields__pgn_headers._get_user_color_from_pgn_headers",
        _raise,
    )

    color, opp_rating, result = _resolve_user_fields__pgn_headers(headers, metadata, "user")
    assert color is None
    assert opp_rating is None
    assert result == ChessGameResult.UNKNOWN.value

    color, opp_rating, result = _resolve_user_fields__pgn_headers(None, metadata, "user")
    assert color is None
    assert opp_rating is None
    assert result == ChessGameResult.UNKNOWN.value


def test_outcome_context_properties() -> None:
    missed = BaseOutcomeContext(
        result=OutcomeResultEnum.MISSED,
        motif="motif",
        best_move=None,
        user_move_uci="e2e4",
        swing=None,
    )
    unclear = BaseOutcomeContext(
        result=OutcomeResultEnum.UNCLEAR,
        motif="motif",
        best_move=None,
        user_move_uci="e2e4",
        swing=None,
    )
    assert missed.was_missed is True
    assert missed.was_unclear is False
    assert unclear.was_unclear is True


def test_sync_postgres_analysis_results(monkeypatch) -> None:
    settings = Settings()

    assert _sync_postgres_analysis_results(None, None, settings) == 0

    recent_rows = [
        {
            "game_id": "g1",
            "position_id": "p1",
            "motif": "fork",
            "severity": 1.0,
            "best_uci": "e2e4",
            "result": "missed",
            "user_uci": "e2e4",
            "eval_delta": 0,
        },
        {
            "game_id": "g2",
            "position_id": "p2",
            "motif": "pin",
            "severity": 1.0,
            "best_uci": "e2e4",
            "result": "missed",
            "user_uci": "e2e4",
            "eval_delta": 0,
        },
    ]

    monkeypatch.setattr(
        "tactix.sync_postgres_analysis_results__pipeline.fetch_recent_tactics",
        lambda *_args, **_kwargs: recent_rows,
    )

    calls = []

    def _upsert(pg_conn, tactic_row, outcome_row):
        if tactic_row["game_id"] == "g2":
            raise RuntimeError("fail")
        calls.append((tactic_row, outcome_row))

    monkeypatch.setattr(
        "tactix.sync_postgres_analysis_results__pipeline.import_module",
        lambda _name: SimpleNamespace(upsert_analysis_tactic_with_outcome=_upsert),
    )

    synced = _sync_postgres_analysis_results(object(), object(), settings)
    assert synced == 1
    assert calls


def test_validate_raw_pgn_hashes(monkeypatch) -> None:
    assert _validate_raw_pgn_hashes([], "lichess", lambda *_: {}) == {"computed": 0, "matched": 0}

    monkeypatch.setattr(
        "tactix.validate_raw_pgn_hashes__pipeline._compute_pgn_hashes",
        lambda *_: {"g1": "hash"},
    )
    monkeypatch.setattr(
        "tactix.validate_raw_pgn_hashes__pipeline._count_hash_matches",
        lambda *_: 1,
    )
    monkeypatch.setattr(
        "tactix.validate_raw_pgn_hashes__pipeline._raise_for_hash_mismatch",
        lambda *_: None,
    )

    def _fetch_latest(ids, source):
        assert ids == ["g1"]
        assert source == "lichess"
        return {"g1": "hash"}

    assert _validate_raw_pgn_hashes([object()], "lichess", _fetch_latest) == {
        "computed": 1,
        "matched": 1,
    }


def test_run_daily_game_sync_delegates(monkeypatch) -> None:
    settings = Settings()

    monkeypatch.setattr(
        "tactix.run_daily_game_sync__pipeline._build_pipeline_settings",
        lambda *_args, **_kwargs: settings,
    )
    monkeypatch.setattr(
        "tactix.run_daily_game_sync__pipeline._build_chess_client",
        lambda *_args, **_kwargs: object(),
    )

    calls = []

    def _capture(context):
        calls.append(context)
        return {"status": "ok"}

    monkeypatch.setattr(
        "tactix.run_daily_game_sync__pipeline._run_daily_game_sync",
        _capture,
    )

    result = run_daily_game_sync(settings, "lichess")
    assert result == {"status": "ok"}
    assert calls


def test_run_daily_game_sync_request(monkeypatch) -> None:
    settings = Settings()

    monkeypatch.setattr(
        "tactix.run_daily_game_sync__pipeline._build_pipeline_settings",
        lambda *_args, **_kwargs: settings,
    )
    monkeypatch.setattr(
        "tactix.run_daily_game_sync__pipeline._build_chess_client",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        "tactix.run_daily_game_sync__pipeline._run_daily_game_sync",
        lambda *_args, **_kwargs: {"status": "ok"},
    )

    request = DailyGameSyncRequest(
        settings=settings,
        source="lichess",
        progress=None,
        profile=None,
        window_start_ms=None,
        window_end_ms=None,
        client=None,
    )
    result = run_daily_game_sync(request)
    assert result == {"status": "ok"}


def test_prepare_dag_helpers() -> None:
    class DummyDagRun:
        conf = {
            "chesscom_profile": "rapid",
            "backfill_start_ms": "10",
            "backfill_end_ms": "20",
            "triggered_at_ms": "15",
        }

    class DummyDagRunNoConf:
        conf = "nope"

    assert _dag_run_conf(None) is None
    assert _dag_run_conf(DummyDagRun()) == DummyDagRun.conf
    assert _dag_run_conf(DummyDagRunNoConf()) is None

    assert resolve_profile(DummyDagRun(), "chesscom") == "rapid"
    assert resolve_profile(DummyDagRun(), "lichess") is None

    assert _coerce_optional_int(b"5") == 5
    assert _coerce_optional_int("bad") is None

    assert _apply_triggered_end(20, 15) == 15
    assert _apply_triggered_end(10, 15) == 10

    start_ms, end_ms, is_backfill = _resolve_backfill_from_interval(
        "backfill",
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 1, 2, tzinfo=UTC),
        None,
        None,
    )
    assert is_backfill is True
    assert start_ms is not None
    assert end_ms is not None

    start_ms, end_ms, is_backfill = _resolve_backfill_from_interval(
        "scheduled",
        None,
        None,
        5,
        None,
    )
    assert (start_ms, end_ms, is_backfill) == (5, None, True)

    resolved = resolve_backfill_window(
        DummyDagRun(),
        "scheduled",
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 1, 2, tzinfo=UTC),
    )
    assert resolved[0] == 10
    assert resolved[1] == 15

    resolved = resolve_backfill_window(None, "scheduled", None, None)
    assert resolved == (None, None, None, False)

    assert to_epoch_ms(datetime(2024, 1, 1, tzinfo=UTC)) == 1704067200000


def test_job_stream_builders_and_metrics_worker(monkeypatch) -> None:
    kwargs = build_stream_job_kwargs(
        job="refresh_metrics",
        source="lichess",
        profile=None,
        backfill_start_ms=10,
        backfill_end_ms=20,
    )
    request = build_stream_job_request(
        job="refresh_metrics",
        source="lichess",
        profile=None,
        backfill_start_ms=10,
        backfill_end_ms=20,
    )
    request_from_values = build_stream_job_request_from_values(kwargs)

    assert request.job == "refresh_metrics"
    assert request_from_values.job == "refresh_metrics"
    assert request_from_values.source == "lichess"

    triggered_at_ms, end_ms = _resolve_backfill_window(10, None)
    assert triggered_at_ms > 0
    assert end_ms is not None

    queue: Queue[object] = Queue()
    sentinel = object()
    settings = Settings()
    context = MetricsStreamContext(
        queue=queue,
        sentinel=sentinel,
        settings=settings,
        filters=MetricsFilters(
            normalized_source="lichess",
            motif=None,
            rating_bucket=None,
            time_control=None,
            start_date=None,
            end_date=None,
        ),
    )

    def _refresh(_settings, source, progress):
        progress({"step": "metrics_refreshed", "job": "refresh_metrics"})
        return {"ok": True}

    monkeypatch.setattr("tactix.job_stream.run_refresh_metrics", _refresh)
    monkeypatch.setattr("tactix.job_stream._refresh_dashboard_cache_async", lambda *_: None)
    monkeypatch.setattr(
        "tactix.job_stream._sources_for_cache_refresh",
        lambda *_: ["lichess"],
    )
    monkeypatch.setattr(
        "tactix.job_stream.get_dashboard_payload",
        lambda *_: {"source": "lichess", "metrics_version": 1, "metrics": {}},
    )

    _stream_metrics_worker(context)

    events = []
    while True:
        item = queue.get()
        if item is sentinel:
            break
        events.append(item)

    event_names = {event for event, _payload in events}
    assert "progress" in event_names
    assert "metrics_update" in event_names
    assert "complete" in event_names


def test_job_stream_queue_helpers() -> None:
    queue: Queue[object] = Queue()
    _queue_job_event(queue, "progress", "job-1", {"step": "start"})
    event, payload = queue.get()
    assert event == "progress"
    assert payload["job"] == "job-1"
    assert payload["job_id"] == "job-1"

    _queue_job_complete(queue, "job-1", "done", result={"ok": True})
    event, payload = queue.get()
    assert event == "complete"
    assert payload["result"]["ok"] is True

    _queue_job_complete(queue, "job-1", "done")
    event, payload = queue.get()
    assert event == "complete"
    assert "result" not in payload

    _queue_job_error(queue, "job-1", "fail")
    event, payload = queue.get()
    assert event == "error"
    assert payload["message"] == "fail"


def test_stream_metrics_response(monkeypatch) -> None:
    settings = Settings()
    filters = SimpleNamespace(rating_bucket=None, time_control=None)

    monkeypatch.setattr(
        "tactix.job_stream._resolve_dashboard_filters",
        lambda _filters: (None, None, "lichess", settings),
    )

    def _fake_thread(*, target, args, daemon):
        class DummyThread:
            def start(self):
                target(*args)

        return DummyThread()

    monkeypatch.setattr("tactix.job_stream.Thread", _fake_thread)
    monkeypatch.setattr(
        "tactix.job_stream._event_stream",
        lambda *_: iter([b"data: ok\n\n"]),
    )
    monkeypatch.setattr("tactix.job_stream._stream_metrics_worker", lambda *_: None)

    response = stream_metrics(filters, motif=None)
    assert isinstance(response, StreamingResponse)


def test_upsert_postgres_raw_pgns_if_enabled(monkeypatch) -> None:
    settings = Settings()

    monkeypatch.setattr(
        "tactix.upsert_postgres_raw_pgns_if_enabled__pipeline.postgres_pgns_enabled",
        lambda _s: False,
    )
    assert _upsert_postgres_raw_pgns_if_enabled(settings, [], None, None) == 0

    monkeypatch.setattr(
        "tactix.upsert_postgres_raw_pgns_if_enabled__pipeline.postgres_pgns_enabled",
        lambda _s: True,
    )
    monkeypatch.setattr(
        "tactix.upsert_postgres_raw_pgns_if_enabled__pipeline.postgres_connection",
        lambda *_: nullcontext(None),
    )
    assert _upsert_postgres_raw_pgns_if_enabled(settings, [], None, None) == 0

    class FakeConn:
        pass

    monkeypatch.setattr(
        "tactix.upsert_postgres_raw_pgns_if_enabled__pipeline.postgres_connection",
        lambda *_: nullcontext(FakeConn()),
    )
    monkeypatch.setattr(
        "tactix.upsert_postgres_raw_pgns_if_enabled__pipeline.init_pgn_schema",
        lambda *_: None,
    )

    class FakeRepo:
        def __init__(self, _conn):
            return None

        def upsert_raw_pgns(self, rows):
            return len(rows)

    monkeypatch.setattr(
        "tactix.upsert_postgres_raw_pgns_if_enabled__pipeline.PostgresRawPgnRepository",
        FakeRepo,
    )
    monkeypatch.setattr(
        "tactix.upsert_postgres_raw_pgns_if_enabled__pipeline._emit_progress",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "tactix.upsert_postgres_raw_pgns_if_enabled__pipeline.record_ops_event",
        lambda *_args, **_kwargs: None,
    )

    inserted = _upsert_postgres_raw_pgns_if_enabled(
        settings,
        [{"game_id": "g1"}],
        None,
        None,
    )
    assert inserted == 1

    class ErrorRepo:
        def __init__(self, _conn):
            return None

        def upsert_raw_pgns(self, _rows):
            raise psycopg2.Error("boom")

    monkeypatch.setattr(
        "tactix.upsert_postgres_raw_pgns_if_enabled__pipeline.PostgresRawPgnRepository",
        ErrorRepo,
    )
    inserted = _upsert_postgres_raw_pgns_if_enabled(
        settings,
        [{"game_id": "g1"}],
        None,
        None,
    )
    assert inserted == 0


def test_maybe_sync_analysis_results(monkeypatch) -> None:
    settings = Settings()
    assert _maybe_sync_analysis_results(None, settings, None, True, 0) == (0, 0)
    assert _maybe_sync_analysis_results(None, settings, object(), False, 0) == (0, 0)
    assert _maybe_sync_analysis_results(None, settings, object(), True, 1) == (0, 1)

    monkeypatch.setattr(
        "tactix.maybe_sync_analysis_results__pipeline._sync_postgres_analysis_results",
        lambda *_args, **_kwargs: 2,
    )
    assert _maybe_sync_analysis_results(None, settings, object(), True, 0) == (2, 2)


def test_pgn_headers_parsing() -> None:
    pgn = (
        '[Event "Test"]\n'
        '[Site "https://example.com"]\n'
        '[Date "2024.01.02"]\n'
        '[Round "1"]\n'
        '[White "User"]\n'
        '[Black "Opp"]\n'
        '[Result "1-0"]\n'
        '[WhiteElo "1200"]\n'
        '[BlackElo "1300"]\n'
        '[TimeControl "300+0"]\n\n'
        "1. e4 e5 2. Nf3 Nc6 1-0"
    )

    headers = PgnHeaders.from_pgn_string(pgn)
    assert headers.round == 1
    assert headers.date == datetime(2024, 1, 2, tzinfo=UTC).date()
    assert headers.white_player == "User"

    assert _parse_pgn_date_str("bad") is None
    with pytest.raises(IndexError):
        PgnHeaders.from_pgn_string(pgn, game_index=5)

    custom_headers = PgnHeaders(
        event="",
        site="",
        date=None,
        time_control=headers.time_control,
        round="x",
    )
    assert custom_headers.round is None


def test_pgn_headers_helpers(tmp_path, monkeypatch, capsys) -> None:
    pgn = (
        '[Event "Test"]\n'
        '[Site "https://example.com"]\n'
        '[Date "2024.01.02"]\n'
        '[Round "1"]\n'
        '[White "User"]\n'
        '[Black "Opp"]\n'
        '[Result "1-0"]\n'
        '[WhiteElo "1200"]\n'
        '[BlackElo "1300"]\n'
        '[TimeControl "300+0"]\n\n'
        "1. e4 e5 2. Nf3 Nc6 1-0"
    )
    file_path = tmp_path / "game.pgn"
    file_path.write_text(pgn, encoding="utf-8")

    headers = PgnHeaders.from_file(str(file_path))
    output = capsys.readouterr().out
    assert "Reading first game" in output
    assert headers.white_player == "User"

    with pytest.raises(IndexError):
        PgnHeaders.from_file(str(file_path), game_index=3)

    chess_headers = chess.pgn.Headers()
    headers_from_chess = PgnHeaders.from_chess_pgn_headers(chess_headers)
    assert headers_from_chess.event == "?"

    all_headers = PgnHeaders.extract_all_from_str(f"{pgn}\n\n{pgn}")
    assert len(all_headers) == 2

    date_headers = PgnHeaders(
        event="",
        site="",
        date=datetime(2024, 1, 1, tzinfo=UTC),
        time_control=headers.time_control,
    )
    assert date_headers.date == datetime(2024, 1, 1, tzinfo=UTC).date()

    def _raise(*_args, **_kwargs):
        raise ValueError("bad")

    monkeypatch.setattr(
        "tactix.pgn_headers._get_game_result_for_user_from_pgn_headers",
        _raise,
    )
    monkeypatch.setattr("tactix.pgn_headers.chess.pgn.read_headers", lambda *_: None)

    headers = PgnHeaders.from_pgn_string(pgn)
    assert headers.result == ChessGameResult.UNKNOWN

    assert _parse_pgn_date_str("") is None
    assert _parse_pgn_date_str("2024.13.40") is None

    bad_date_headers = PgnHeaders(
        event="",
        site="",
        date="bad",
        time_control=headers.time_control,
    )
    assert bad_date_headers.date is None

    monkeypatch.setattr("tactix.pgn_headers.Now.to_utc", lambda *_: None)
    assert _coerce_pgn_datetime(datetime(2024, 1, 1, tzinfo=UTC)) is None


def test_trigger_airflow_daily_sync_context(monkeypatch) -> None:
    settings = Settings()
    context = AirflowDailySyncTriggerContext(
        settings=settings,
        source="lichess",
        profile=None,
        backfill_start_ms=None,
        backfill_end_ms=None,
        triggered_at_ms=None,
    )

    monkeypatch.setattr(
        "tactix.trigger_airflow_daily_sync__airflow_jobs.orchestrate_dag_run__airflow_trigger",
        lambda *_args, **_kwargs: {"dag_run_id": "run-1"},
    )
    monkeypatch.setattr(
        "tactix.trigger_airflow_daily_sync__airflow_jobs._airflow_conf",
        lambda *_args, **_kwargs: {"ok": True},
    )
    monkeypatch.setattr(
        "tactix.trigger_airflow_daily_sync__airflow_jobs._airflow_run_id",
        lambda payload: payload["dag_run_id"],
    )

    assert _trigger_airflow_daily_sync(context) == "run-1"


def test_engine_result_helpers() -> None:
    board = chess.Board()
    info = {
        "score": chess.engine.PovScore(chess.engine.Cp(50), chess.WHITE),
        "depth": 12,
        "pv": [chess.Move.from_uci("e2e4")],
    }
    result = EngineResult.from_engine_result(info, board)
    assert result.best_move == chess.Move.from_uci("e2e4")
    assert result.score_cp == 50
    assert result.depth == 12

    board.turn = chess.BLACK
    info_list = [
        {"multipv": 2, "score": chess.engine.Cp(25)},
        {"multipv": 1, "score": chess.engine.Cp(30)},
    ]
    result = EngineResult.from_engine_result(info_list, board)
    assert result.score_cp == -30

    empty = EngineResult.from_engine_result({}, board)
    assert empty.best_move is None

    score_only = EngineResult.from_engine_result({"score": chess.engine.Cp(10)}, None)
    assert score_only.score_cp == 10

    missing_score = EngineResult.from_engine_result({"score": "bad"}, None)
    assert missing_score.score_cp == 0


def test_tactics_outcome_helpers() -> None:
    assert should_override_failed_attempt("unclear", -5, 0, "fork") is True
    assert should_override_failed_attempt("missed", -5, 0, "fork") is False

    params = UnclearOutcomeParams(
        motif="fork",
        best_move="e2e4",
        user_move_uci="e2e4",
        swing=10,
        threshold=5,
    )
    context, threshold = resolve_unclear_outcome_context(
        "unclear",
        None,
        (),
        params,
        {},
    )
    assert context.motif == "fork"
    assert threshold == 5

    base_context = BaseOutcomeContext(
        result=OutcomeResultEnum.UNCLEAR,
        motif="fork",
        best_move=None,
        user_move_uci="e2e4",
        swing=1,
    )
    context, threshold = resolve_unclear_outcome_context(
        base_context,
        3,
        (),
        None,
        {},
    )
    assert context is base_context
    assert threshold == 3

    context, threshold = resolve_unclear_outcome_context(
        base_context,
        None,
        (5,),
        None,
        {},
    )
    assert context is base_context
    assert threshold == 5

    with pytest.raises(TypeError):
        resolve_unclear_outcome_context(
            "unclear",
            None,
            ("a", "b", "c", "d", "e", "f"),
            None,
            {},
        )

    with pytest.raises(TypeError):
        resolve_unclear_outcome_context("unclear", None, (), None, {"extra": "x"})

    with pytest.raises(TypeError):
        resolve_unclear_outcome_context(
            "unclear",
            "motif",
            (),
            UnclearOutcomeParams(motif="pin"),
            {},
        )

    with pytest.raises(TypeError):
        resolve_unclear_outcome_context("unclear", None, (), None, {})

    with pytest.raises(TypeError):
        resolve_unclear_outcome_context(
            "unclear",
            5,
            (),
            UnclearOutcomeParams(threshold=3),
            {},
        )

    with pytest.raises(TypeError):
        resolve_unclear_outcome_context("unclear", 3.5, (), None, {})

    values = dict.fromkeys(("motif", "best_move", "user_move_uci", "swing", "threshold"))
    _apply_unclear_args(values, ("fork",))
    with pytest.raises(TypeError):
        _apply_unclear_args(values, ("pin",))

    values = {"threshold": 1}
    with pytest.raises(TypeError):
        _apply_int_threshold(values, 2)

    values = dict.fromkeys(("motif", "best_move", "user_move_uci", "swing", "threshold"))
    _apply_unclear_threshold(values, "mate")
    assert values["motif"] == "mate"
    with pytest.raises(TypeError):
        _apply_unclear_threshold(values, 3.5)


def test_persist_raw_pgns(monkeypatch) -> None:
    settings = Settings()
    progress_calls = []
    delete_calls = []

    class Repo:
        def upsert_raw_pgns(self, rows):
            return len(rows)

        def fetch_latest_pgn_hashes(self, ids, _source):
            return {game_id: "hash" for game_id in ids}

    monkeypatch.setattr(
        "tactix.persist_raw_pgns__pipeline.raw_pgn_repository",
        lambda _conn: Repo(),
    )
    monkeypatch.setattr(
        "tactix.persist_raw_pgns__pipeline._validate_raw_pgn_hashes",
        lambda *_args, **_kwargs: {"computed": 1, "matched": 1},
    )
    monkeypatch.setattr(
        "tactix.persist_raw_pgns__pipeline._build_games_table_row",
        lambda row: row,
    )
    monkeypatch.setattr(
        "tactix.persist_raw_pgns__pipeline.delete_game_rows",
        lambda *_args, **_kwargs: delete_calls.append("deleted"),
    )
    monkeypatch.setattr(
        "tactix.persist_raw_pgns__pipeline.upsert_games",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "tactix.persist_raw_pgns__pipeline._emit_progress",
        lambda *_args, **_kwargs: progress_calls.append("progress"),
    )
    monkeypatch.setattr(
        "tactix.persist_raw_pgns__pipeline.record_ops_event",
        lambda *_args, **_kwargs: None,
    )

    context = PersistRawPgnsContext(
        conn=object(),
        games_to_process=[{"game_id": "g1", "pgn": "1. e4"}],
        settings=settings,
        progress=None,
        profile=None,
        delete_existing=True,
        emit_start=True,
    )
    result = _persist_raw_pgns(context)
    assert result == (1, 1, 1)
    assert delete_calls
    assert progress_calls


def test_extract_last_timestamp_ms(monkeypatch) -> None:
    pgn = '[Event "Test"]\n[Date "2024.01.02"]\n[EndTime "12:34:56"]\n\n1. e4 e5 1-0'
    timestamp = extract_last_timestamp_ms(pgn)
    expected = int(datetime(2024, 1, 2, 12, 34, 56, tzinfo=UTC).timestamp() * 1000)
    assert timestamp == expected

    monkeypatch.setattr("tactix.extract_last_timestamp_ms.time.time", lambda: 0)
    assert extract_last_timestamp_ms("") == 0

    pgn_no_date = '[Event "Test"]\n\n1. e4 e5 1-0'
    monkeypatch.setattr("tactix.extract_last_timestamp_ms.time.time", lambda: 5)
    assert extract_last_timestamp_ms(pgn_no_date) == 5000

    monkeypatch.setattr(
        "tactix.extract_last_timestamp_ms._parse_utc_start_ms",
        lambda *_args, **_kwargs: None,
    )
    assert _parse_utc_header_timestamp({"UTCDate": "2024.01.02", "UTCTime": "00:00:00"}) is None

    monkeypatch.setattr("tactix.extract_last_timestamp_ms.time.time", lambda: 7)
    assert _parse_date_header_timestamp({}) == 7000


def test_call_rust_extractor_uses_fallback(monkeypatch) -> None:
    request = ExtractorRequest(
        pgn='[SetUp "1"]\n\n1. e4 e5',
        user="user",
        source="lichess",
        game_id=None,
        side_to_move_filter=None,
    )

    monkeypatch.setattr(
        "tactix.extract_positions__pgn._extract_positions_fallback",
        lambda _req: [{"position_id": "p1"}],
    )

    result = _call_rust_extractor(lambda *_args, **_kwargs: [], request)
    assert result == [{"position_id": "p1"}]


def test_init_analysis_schema_if_needed(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(
        "tactix.init_analysis_schema_if_needed__pipeline.init_analysis_schema",
        lambda *_args, **_kwargs: calls.append("called"),
    )

    _init_analysis_schema_if_needed(None, True)
    _init_analysis_schema_if_needed(object(), False)
    _init_analysis_schema_if_needed(object(), True)
    assert calls == ["called"]


def test_load_fixture_games(monkeypatch, tmp_path) -> None:
    request = FixtureGamesRequest(
        fixture_path=tmp_path / "missing.pgn",
        user="user",
        source="lichess",
        since_ms=0,
    )
    assert load_fixture_games(request) == []

    fixture_path = tmp_path / "fixture.pgn"
    fixture_path.write_text('[Event "Test"]\n\n1. e4 e5', encoding="utf-8")

    monkeypatch.setattr(
        "tactix.load_fixture_games.split_pgn_chunks",
        lambda *_args, **_kwargs: ["pgn"],
    )
    monkeypatch.setattr(
        "tactix.load_fixture_games._filter_fixture_games",
        lambda *_args, **_kwargs: [{"game_id": "g1"}],
    )
    monkeypatch.setattr(
        "tactix.load_fixture_games._coerce_fixture_rows",
        lambda rows, _coerce: rows,
    )

    games = load_fixture_games(str(fixture_path), "user", "lichess", 0)
    assert games == [{"game_id": "g1"}]

    with pytest.raises(TypeError):
        load_fixture_games(str(fixture_path))


def test_stream_job_context_builders() -> None:
    settings = Settings()
    queue: Queue[object] = Queue()

    values = _collect_stream_job_values(
        (queue, "daily_game_sync", "lichess", None, 10, 20, 123, None),
        {},
    )
    context = _build_stream_job_context(settings, values)
    assert context.job == "daily_game_sync"
    assert context.window.triggered_at_ms == 123
    context.progress({"step": "start"})

    with pytest.raises(TypeError):
        _build_stream_job_context(
            settings,
            {
                "queue": None,
                "job": None,
                "triggered_at_ms": None,
                "progress": None,
                "source": None,
                "profile": None,
                "backfill_start_ms": None,
                "backfill_end_ms": None,
            },
        )


def test_chesscom_candidate_href() -> None:
    assert _extract_candidate_href("https://example.com") == "https://example.com"
    assert _extract_candidate_href({"href": "https://example.com"}) == "https://example.com"
    assert _extract_candidate_href({"url": "https://example.com"}) == "https://example.com"
    assert _extract_candidate_href({"href": ""}) is None
    assert _extract_candidate_href(123) is None
