from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from tactix.app.use_cases.dashboard import DashboardUseCase
from tactix.app.use_cases.pipeline_run import PipelineRunUseCase
from tactix.app.use_cases.postgres import PostgresUseCase
from tactix.app.use_cases.practice import GameNotFoundError, PracticeAttemptError, PracticeUseCase
from tactix.app.use_cases.tactics_search import TacticsSearchUseCase
from tactix.dashboard_query_filters import DashboardQueryFilters
from tactix.pipeline_run_filters import PipelineRunFilters
from tactix.tactics_search_filters import TacticsSearchFilters


class DummyUnitOfWork:
    def __init__(self, conn) -> None:
        self._conn = conn
        self.begin_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0
        self.close_calls = 0

    def begin(self):
        self.begin_calls += 1
        return self._conn

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.close_calls += 1


def test_dashboard_use_case_returns_cached_payload(tmp_path) -> None:
    payload = {"status": "ok", "metrics_version": 5}
    settings = SimpleNamespace(duckdb_path=tmp_path / "tactix.duckdb", data_dir=tmp_path)
    use_case = DashboardUseCase(
        resolve_dashboard_filters=lambda _filters: (None, None, None, settings),
        dashboard_cache_key=lambda _settings, _query: ("key",),
        get_cached_dashboard_payload=lambda _key: payload,
        get_dashboard_payload=MagicMock(),
        set_dashboard_cache=MagicMock(),
    )

    result = use_case.get_dashboard(DashboardQueryFilters(), None)

    assert result == payload
    use_case.get_dashboard_payload.assert_not_called()


def test_dashboard_use_case_summary_uses_counts(tmp_path) -> None:
    settings = SimpleNamespace(duckdb_path=tmp_path / "tactix.duckdb", data_dir=tmp_path)
    conn = MagicMock()
    uow = DummyUnitOfWork(conn)
    counts = {"games": 12}
    use_case = DashboardUseCase(
        resolve_dashboard_filters=lambda _filters: (None, None, None, settings),
        unit_of_work_factory=lambda _path: uow,
        init_schema=MagicMock(),
        fetch_pipeline_table_counts=lambda _conn, _query: counts,
    )

    result = use_case.get_summary(DashboardQueryFilters(), "custom")

    assert result == {"source": "all", "summary": counts}
    assert settings.duckdb_path == tmp_path / "custom.duckdb"
    assert uow.commit_calls == 1
    assert uow.rollback_calls == 0
    assert uow.close_calls == 1


def test_practice_use_case_game_detail_not_found(tmp_path) -> None:
    settings = SimpleNamespace(
        duckdb_path=tmp_path / "tactix.duckdb",
        source="lichess",
        user="tester",
    )
    repo = MagicMock()
    repo.fetch_game_detail.return_value = {"pgn": ""}
    uow = DummyUnitOfWork(MagicMock())
    use_case = PracticeUseCase(
        get_settings=lambda **_kwargs: settings,
        unit_of_work_factory=lambda _path: uow,
        init_schema=MagicMock(),
        repository_factory=lambda _conn: repo,
    )

    try:
        use_case.get_game_detail("game-1", "lichess")
    except GameNotFoundError as exc:
        assert "Game not found" in str(exc)
    else:
        raise AssertionError("Expected GameNotFoundError")


def test_practice_use_case_submit_attempt_errors(tmp_path) -> None:
    settings = SimpleNamespace(
        duckdb_path=tmp_path / "tactix.duckdb",
        source="lichess",
        user="tester",
    )
    repo = MagicMock()
    repo.grade_practice_attempt.side_effect = ValueError("bad")
    uow = DummyUnitOfWork(MagicMock())
    use_case = PracticeUseCase(
        get_settings=lambda **_kwargs: settings,
        unit_of_work_factory=lambda _path: uow,
        init_schema=MagicMock(),
        repository_factory=lambda _conn: repo,
        time_provider=lambda: 1.0,
    )
    payload = SimpleNamespace(
        tactic_id=1,
        position_id=2,
        attempted_uci="e2e4",
        served_at_ms=None,
        source="lichess",
    )

    try:
        use_case.submit_attempt(payload)
    except PracticeAttemptError as exc:
        assert "bad" in str(exc)
    else:
        raise AssertionError("Expected PracticeAttemptError")


def test_tactics_search_use_case_returns_payload(tmp_path) -> None:
    settings = SimpleNamespace(duckdb_path=tmp_path / "tactix.duckdb", source="lichess")
    tactics = [{"tactic_id": 1}]
    uow = DummyUnitOfWork(MagicMock())
    use_case = TacticsSearchUseCase(
        get_settings=lambda **_kwargs: settings,
        unit_of_work_factory=lambda _path: uow,
        init_schema=MagicMock(),
        fetch_recent_tactics=lambda _conn, _query, limit: tactics,
        coerce_date_to_datetime=lambda _value, end_of_day=False: None,
        normalize_source=lambda _source: None,
    )

    result = use_case.search(TacticsSearchFilters(), 5)

    assert result == {"source": "all", "limit": 5, "tactics": tactics}


def test_pipeline_run_use_case_runs_and_returns_counts(tmp_path) -> None:
    settings = SimpleNamespace(
        duckdb_path=tmp_path / "tactix.duckdb",
        data_dir=tmp_path,
        source="lichess",
        user="tester",
        lichess=SimpleNamespace(user="tester"),
        chesscom=SimpleNamespace(user="tester", token="token", profile=None, time_class=None),
        chesscom_use_fixture_when_no_token=False,
        stockfish_movetime_ms=50,
        stockfish_depth=8,
        stockfish_multipv=1,
    )
    conn = MagicMock()
    uow = DummyUnitOfWork(conn)
    use_case = PipelineRunUseCase(
        get_settings=lambda **_kwargs: settings,
        normalize_source=lambda _source: "lichess",
        coerce_date_to_datetime=lambda _value, end_of_day=False: None,
        run_daily_game_sync=lambda *_args, **_kwargs: {"status": "ok"},
        refresh_dashboard_cache_async=MagicMock(),
        sources_for_cache_refresh=lambda _source: {"lichess"},
        fetch_pipeline_table_counts=lambda _conn, _query: {"games": 1},
        fetch_opportunity_motif_counts=lambda _conn, _query: {"fork": 2},
        unit_of_work_factory=lambda _path: uow,
        init_schema=MagicMock(),
    )

    result = use_case.run(PipelineRunFilters())

    assert result["status"] == "ok"
    assert isinstance(result["run_id"], str)
    assert result["counts"] == {"games": 1}
    assert result["motif_counts"] == {"fork": 2}
    use_case.refresh_dashboard_cache_async.assert_called_once()
    assert uow.commit_calls == 1
    assert uow.rollback_calls == 0
    assert uow.close_calls == 1


def test_postgres_use_case_status_payload() -> None:
    repo = MagicMock()
    repo.get_status.return_value = "status"
    repo.fetch_ops_events.return_value = []
    use_case = PostgresUseCase(
        get_settings=lambda: "settings",
        repository_factory=lambda _settings, _uow_factory: repo,
        serialize_status=lambda _status: {"status": "ok"},
    )

    result = use_case.get_status(5)

    assert result == {"status": "ok", "events": []}
    repo.fetch_ops_events.assert_called_once_with(limit=5)
