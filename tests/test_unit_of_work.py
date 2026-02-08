from __future__ import annotations

from unittest.mock import MagicMock, patch

from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.duckdb_unit_of_work import DuckDbUnitOfWork
from tactix.db.postgres_unit_of_work import PostgresUnitOfWork
from tactix.config import Settings


def test_duckdb_unit_of_work_commit_persists(tmp_path) -> None:
    db_path = tmp_path / "uow.duckdb"
    uow = DuckDbUnitOfWork(db_path)
    conn = uow.begin()
    init_schema(conn)
    conn.execute("CREATE TABLE IF NOT EXISTS uow_test (id INTEGER)")
    conn.execute("INSERT INTO uow_test VALUES (1)")
    uow.commit()
    uow.close()

    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) FROM uow_test").fetchone()
        assert row[0] == 1
    finally:
        conn.close()


def test_duckdb_unit_of_work_rollback_discards(tmp_path) -> None:
    db_path = tmp_path / "uow.duckdb"
    conn = get_connection(db_path)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS uow_test (id INTEGER)")
        conn.execute("INSERT INTO uow_test VALUES (1)")
    finally:
        conn.close()

    uow = DuckDbUnitOfWork(db_path)
    conn = uow.begin()
    conn.execute("INSERT INTO uow_test VALUES (2)")
    uow.rollback()
    uow.close()

    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) FROM uow_test").fetchone()
        assert row[0] == 1
    finally:
        conn.close()


def test_postgres_unit_of_work_begins_transaction() -> None:
    settings = Settings()
    settings.postgres_host = "localhost"
    settings.postgres_db = "tactix"
    settings.postgres_user = "tactix"
    settings.postgres_password = "tactix"
    conn = MagicMock()
    conn.autocommit = True
    with patch("tactix.db.postgres_unit_of_work._connection_kwargs", return_value={"host": "x"}):
        with patch("tactix.db.postgres_unit_of_work.psycopg2.connect", return_value=conn):
            uow = PostgresUnitOfWork(settings)
            resolved = uow.begin()
            assert resolved is conn
            assert conn.autocommit is False
            uow.commit()
            conn.commit.assert_called_once()
            uow.close()


def test_postgres_unit_of_work_returns_none_when_disabled() -> None:
    settings = Settings()
    settings.postgres_host = None
    settings.postgres_db = None
    uow = PostgresUnitOfWork(settings)
    assert uow.begin() is None
    uow.commit()
    uow.rollback()
    uow.close()
