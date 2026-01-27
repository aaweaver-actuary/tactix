from unittest.mock import MagicMock, patch

from tactix.config import Settings
from tactix.postgres_store import (
    PostgresStatus,
    fetch_ops_events,
    fetch_analysis_tactics,
    get_postgres_status,
    init_analysis_schema,
    postgres_analysis_enabled,
    postgres_enabled,
    record_ops_event,
    serialize_status,
    upsert_analysis_tactic_with_outcome,
)


def _make_settings() -> Settings:
    settings = Settings()
    settings.postgres_host = "localhost"
    settings.postgres_db = "tactix"
    settings.postgres_user = "tactix"
    settings.postgres_password = "tactix"
    return settings


def test_postgres_enabled_with_host() -> None:
    settings = _make_settings()
    assert postgres_enabled(settings) is True


def test_postgres_analysis_disabled_with_flag() -> None:
    settings = _make_settings()
    settings.postgres_analysis_enabled = False
    assert postgres_analysis_enabled(settings) is False


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
    with patch("tactix.postgres_store.psycopg2.connect", side_effect=Exception("boom")):
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
    ]
    conn = MagicMock()
    conn.cursor.return_value = cursor
    with patch("tactix.postgres_store.psycopg2.connect", return_value=conn):
        status = get_postgres_status(settings)
    assert status.status == "ok"
    assert status.schema == "tactix_ops,tactix_analysis"
    assert status.tables == [
        "tactix_ops.ops_events",
        "tactix_analysis.tactics",
        "tactix_analysis.tactic_outcomes",
    ]


def test_init_analysis_schema_creates_tables() -> None:
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    conn = MagicMock()
    conn.cursor.return_value = cursor

    init_analysis_schema(conn)

    cursor.execute.assert_any_call("CREATE SCHEMA IF NOT EXISTS tactix_analysis")


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
    with patch("tactix.postgres_store.psycopg2.connect", return_value=conn):
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
    with patch("tactix.postgres_store.psycopg2.connect", return_value=conn):
        events = fetch_ops_events(settings, limit=1)
    assert len(events) == 1
    assert events[0]["event_type"] == "daily_game_sync_start"
