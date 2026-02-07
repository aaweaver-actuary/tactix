from unittest.mock import MagicMock, patch

from tactix.db.postgres_repository import (
    PostgresRepository,
    PostgresRepositoryDependencies,
)
from tactix.postgres_status import PostgresStatus
from tactix.config import Settings
from tactix.fetch_analysis_tactics import fetch_analysis_tactics
from tactix.fetch_ops_events import fetch_ops_events
from tactix.db.postgres_raw_pgn_repository import (
    PostgresRawPgnRepository,
    fetch_postgres_raw_pgns_summary,
)
from tactix.get_postgres_status import get_postgres_status
from tactix.init_analysis_schema import init_analysis_schema
from tactix.init_pgn_schema import init_pgn_schema
from tactix.postgres_analysis_enabled import postgres_analysis_enabled
from tactix.postgres_enabled import postgres_enabled
from tactix.postgres_pgns_enabled import postgres_pgns_enabled
from tactix.record_ops_event import record_ops_event
from tactix.upsert_analysis_tactic_with_outcome import upsert_analysis_tactic_with_outcome
from tactix.serialize_status import (
    serialize_status,
)


def _make_settings() -> Settings:
    settings = Settings()
    settings.postgres_host = "localhost"
    settings.postgres_db = "tactix"
    settings.postgres_user = "tactix"
    settings.postgres_password = "tactix"
    return settings


def _make_repository(
    settings: Settings | None = None,
    dependencies: PostgresRepositoryDependencies | None = None,
) -> tuple[PostgresRepository, PostgresRepositoryDependencies]:
    resolved = settings or _make_settings()
    if dependencies is None:
        dependencies = PostgresRepositoryDependencies(
            get_status=MagicMock(),
            fetch_ops_events=MagicMock(),
            fetch_analysis_tactics=MagicMock(),
            fetch_raw_pgns_summary=MagicMock(),
        )
    return PostgresRepository(resolved, dependencies=dependencies), dependencies


def test_postgres_enabled_with_host() -> None:
    settings = _make_settings()
    assert postgres_enabled(settings) is True


def test_postgres_analysis_disabled_with_flag() -> None:
    settings = _make_settings()
    settings.postgres_analysis_enabled = False
    assert postgres_analysis_enabled(settings) is False


def test_postgres_pgns_disabled_with_flag() -> None:
    settings = _make_settings()
    settings.postgres_pgns_enabled = False
    assert postgres_pgns_enabled(settings) is False


def test_postgres_disabled_without_host() -> None:
    settings = Settings()
    settings.postgres_host = None
    settings.postgres_db = None
    assert postgres_enabled(settings) is False


def test_serialize_status_includes_optional_fields() -> None:
    status = PostgresStatus(
        enabled=True,
        status="ok",
        latency_ms=12.5,
        schema="tactix_ops",
        tables=["ops_events"],
    )
    payload = serialize_status(status)
    assert payload["enabled"] is True
    assert payload["status"] == "ok"
    assert payload["latency_ms"] == 12.5
    assert payload["schema"] == "tactix_ops"
    assert payload["tables"] == ["ops_events"]


def test_get_postgres_status_disabled() -> None:
    settings = Settings()
    settings.postgres_host = None
    settings.postgres_db = None
    status = get_postgres_status(settings)
    assert status.enabled is False
    assert status.status == "disabled"


def test_get_postgres_status_unreachable() -> None:
    settings = _make_settings()
    with patch(
        "tactix.get_postgres_status.psycopg2.connect",
        side_effect=Exception("boom"),
    ):
        status = get_postgres_status(settings)
    assert status.enabled is True
    assert status.status == "unreachable"
    assert status.error


def test_get_postgres_status_ok_with_tables() -> None:
    settings = _make_settings()
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchall.side_effect = [
        [("ops_events",)],
        [("tactics",), ("tactic_outcomes",)],
        [("raw_pgns",)],
    ]
    conn = MagicMock()
    conn.cursor.return_value = cursor
    with patch("tactix.get_postgres_status.psycopg2.connect", return_value=conn):
        status = get_postgres_status(settings)
    assert status.status == "ok"
    assert status.schema == "tactix_ops,tactix_analysis,tactix_pgns"
    assert status.tables == [
        "tactix_ops.ops_events",
        "tactix_analysis.tactics",
        "tactix_analysis.tactic_outcomes",
        "tactix_pgns.raw_pgns",
    ]


def test_init_analysis_schema_creates_tables() -> None:
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    conn = MagicMock()
    conn.cursor.return_value = cursor

    init_analysis_schema(conn)

    cursor.execute.assert_any_call("CREATE SCHEMA IF NOT EXISTS tactix_analysis")


def test_init_pgn_schema_creates_tables() -> None:
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    conn = MagicMock()
    conn.cursor.return_value = cursor

    init_pgn_schema(conn)

    cursor.execute.assert_any_call("CREATE SCHEMA IF NOT EXISTS tactix_pgns")


def test_upsert_postgres_raw_pgns_inserts_new_version() -> None:
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchone.return_value = None
    cursor.rowcount = 1
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.autocommit = True

    repo = PostgresRawPgnRepository(conn)
    inserted = repo.upsert_raw_pgns(
        [
            {
                "game_id": "game-1",
                "source": "lichess",
                "user": "alice",
                "pgn": '[Event "Test"]\n\n1. e4 *',
                "last_timestamp_ms": 1,
            }
        ],
    )

    assert inserted == 1
    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()
    assert conn.autocommit is True
    assert any(
        "INSERT INTO tactix_pgns.raw_pgns" in str(call.args[0])
        for call in cursor.execute.call_args_list
    )


def test_upsert_postgres_raw_pgns_skips_duplicate_hash() -> None:
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchone.return_value = ("match", 2)
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.autocommit = True

    with patch("tactix._build_pgn_upsert_plan.BaseDbStore.hash_pgn", return_value="match"):
        repo = PostgresRawPgnRepository(conn)
        inserted = repo.upsert_raw_pgns(
            [
                {
                    "game_id": "game-1",
                    "source": "lichess",
                    "user": "alice",
                    "pgn": '[Event "Test"]\n\n1. e4 *',
                    "last_timestamp_ms": 1,
                }
            ],
        )

    assert inserted == 0
    assert not any(
        "INSERT INTO tactix_pgns.raw_pgns" in str(call.args[0])
        for call in cursor.execute.call_args_list
    )


def test_fetch_postgres_raw_pgns_summary_returns_totals() -> None:
    settings = _make_settings()
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchall.return_value = [
        {
            "source": "lichess",
            "total_rows": 2,
            "distinct_games": 2,
            "latest_ingested_at": "2026-01-27T00:00:00Z",
        }
    ]
    cursor.fetchone.return_value = {
        "total_rows": 2,
        "distinct_games": 2,
        "latest_ingested_at": "2026-01-27T00:00:00Z",
    }
    conn = MagicMock()
    conn.cursor.return_value = cursor
    with patch("tactix.postgres_connection.psycopg2.connect", return_value=conn):
        payload = fetch_postgres_raw_pgns_summary(settings)

    assert payload["status"] == "ok"
    assert payload["total_rows"] == 2
    assert payload["distinct_games"] == 2
    assert payload["sources"][0]["source"] == "lichess"


def test_postgres_repository_get_status_delegates() -> None:
    settings = _make_settings()
    repo, deps = _make_repository(settings=settings)
    deps.get_status.return_value = PostgresStatus(enabled=True, status="ok")
    status = repo.get_status()
    assert status.status == "ok"
    deps.get_status.assert_called_once_with(settings)


def test_postgres_repository_fetch_ops_events_delegates() -> None:
    settings = _make_settings()
    repo, deps = _make_repository(settings=settings)
    deps.fetch_ops_events.return_value = [{"event_type": "test"}]
    events = repo.fetch_ops_events(limit=5)
    assert events == [{"event_type": "test"}]
    deps.fetch_ops_events.assert_called_once_with(settings, 5)


def test_postgres_repository_fetch_analysis_tactics_delegates() -> None:
    settings = _make_settings()
    repo, deps = _make_repository(settings=settings)
    deps.fetch_analysis_tactics.return_value = [{"tactic_id": 1}]
    tactics = repo.fetch_analysis_tactics(limit=12)
    assert tactics == [{"tactic_id": 1}]
    deps.fetch_analysis_tactics.assert_called_once_with(settings, 12)


def test_postgres_repository_fetch_raw_pgns_summary_delegates() -> None:
    settings = _make_settings()
    repo, deps = _make_repository(settings=settings)
    deps.fetch_raw_pgns_summary.return_value = {"status": "ok"}
    summary = repo.fetch_raw_pgns_summary()
    assert summary == {"status": "ok"}
    deps.fetch_raw_pgns_summary.assert_called_once_with(settings)


def test_fetch_postgres_raw_pgns_summary_disabled() -> None:
    settings = _make_settings()
    settings.postgres_pgns_enabled = False
    payload = fetch_postgres_raw_pgns_summary(settings)
    assert payload["status"] == "disabled"


def test_upsert_analysis_tactic_with_outcome_inserts() -> None:
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchone.return_value = (42,)
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.autocommit = True

    tactic_id = upsert_analysis_tactic_with_outcome(
        conn,
        {
            "position_id": 10,
            "game_id": "game-1",
            "motif": "fork",
            "severity": 1.2,
            "best_uci": "e2e4",
            "best_san": "e4",
            "explanation": "Forks the queen and rook",
            "eval_cp": 120,
        },
        {"result": "found", "user_uci": "e2e4", "eval_delta": 80},
    )

    assert tactic_id == 42
    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()
    assert conn.autocommit is True


def test_fetch_analysis_tactics_returns_rows() -> None:
    settings = _make_settings()
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchall.return_value = [{"tactic_id": 1, "motif": "fork"}]
    conn = MagicMock()
    conn.cursor.return_value = cursor
    with patch("tactix.postgres_connection.psycopg2.connect", return_value=conn):
        rows = fetch_analysis_tactics(settings, limit=1)
    assert rows == [{"tactic_id": 1, "motif": "fork"}]


def test_record_ops_event_no_connection() -> None:
    settings = Settings()
    settings.postgres_host = None
    settings.postgres_db = None
    assert record_ops_event(settings, component="api", event_type="start") is False


def test_fetch_ops_events_with_rows() -> None:
    settings = _make_settings()
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchall.return_value = [
        {
            "id": 1,
            "component": "api",
            "event_type": "daily_game_sync_start",
            "source": "lichess",
            "profile": None,
            "metadata": {},
            "created_at": "2026-01-27T00:00:00Z",
        }
    ]
    conn = MagicMock()
    conn.cursor.return_value = cursor
    with patch("tactix.postgres_connection.psycopg2.connect", return_value=conn):
        events = fetch_ops_events(settings, limit=1)
    assert len(events) == 1
    assert events[0]["event_type"] == "daily_game_sync_start"
