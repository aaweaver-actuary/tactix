"""Tests for run_migrations pipeline."""

from __future__ import annotations

from dataclasses import dataclass

import tactix.run_migrations__pipeline as run_migrations


@dataclass
class DummySettings:
    source: str = "lichess"
    duckdb_path: str = "/tmp/duck.db"

    def ensure_dirs(self) -> None:
        return None


def test_run_migrations_sets_source(monkeypatch) -> None:
    dummy = DummySettings()

    monkeypatch.setattr(run_migrations, "get_settings", lambda source=None: dummy)
    monkeypatch.setattr(run_migrations, "get_connection", lambda _path: object())
    monkeypatch.setattr(run_migrations, "migrate_schema", lambda _conn: None)
    monkeypatch.setattr(run_migrations, "get_schema_version", lambda _conn: 42)
    monkeypatch.setattr(run_migrations, "_emit_progress", lambda *_args, **_kwargs: None)

    result = run_migrations.run_migrations(source="chesscom")

    assert dummy.source == "chesscom"
    assert result == {"source": "chesscom", "schema_version": 42}
