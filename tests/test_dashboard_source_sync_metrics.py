from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tactix.config import Settings
from tactix.db.duckdb_store import DuckDbStore, get_connection, init_schema
from tactix.db.raw_pgn_repository_provider import upsert_raw_pgns
from tactix.define_base_db_store_context__db_store import BaseDbStoreContext
from tactix.utils.logger import Logger

PGN_TEMPLATE = "1. e4 *"


def _timestamp_ms(days_ago: int, *, offset_ms: int = 0) -> int:
    value = datetime.now(tz=UTC) - timedelta(days=days_ago)
    return int(value.timestamp() * 1000) + offset_ms


def _insert_games(
    conn,
    *,
    source: str,
    total: int,
    days_ago: int,
    prefix: str,
) -> None:
    rows = []
    for idx in range(total):
        game_id = f"{prefix}-{idx}"
        rows.append(
            {
                "game_id": game_id,
                "user": "tester",
                "source": source,
                "pgn": PGN_TEMPLATE,
                "last_timestamp_ms": _timestamp_ms(days_ago, offset_ms=idx),
            }
        )
    upsert_raw_pgns(conn, rows)


def _build_store(tmp_path: Path) -> DuckDbStore:
    settings = Settings(
        user="tester",
        source="lichess",
        duckdb_path=tmp_path / "tactix.duckdb",
        checkpoint_path=tmp_path / "since.txt",
        metrics_version_file=tmp_path / "metrics.txt",
    )
    return DuckDbStore(
        BaseDbStoreContext(settings=settings, logger=Logger("test")),
        db_path=settings.duckdb_path,
    )


def _prepare_payload(*, rows: list[tuple[str, int, int, str]]) -> dict[str, object]:
    tmp_dir = Path(tempfile.mkdtemp())
    db_path = tmp_dir / "tactix.duckdb"
    conn = get_connection(db_path)
    init_schema(conn)
    try:
        for source, total, days_ago, prefix in rows:
            _insert_games(conn, source=source, total=total, days_ago=days_ago, prefix=prefix)
        return _build_store(tmp_dir).get_dashboard_payload(source="all")
    finally:
        conn.close()


def test_dashboard_source_sync_counts_last_90_days_for_both_accounts() -> None:
    payload = _prepare_payload(
        rows=[
            ("lichess", 72, 10, "l90"),
            ("chesscom", 81, 20, "c90"),
            ("lichess", 15, 120, "lold"),
            ("chesscom", 11, 150, "cold"),
        ],
    )
    source_sync = payload["source_sync"]
    assert source_sync["window_days"] == 90
    rows_by_source = {row["source"]: row for row in source_sync["sources"]}

    assert rows_by_source["lichess"]["games_played"] == 72
    assert rows_by_source["lichess"]["synced"] is True
    assert isinstance(rows_by_source["lichess"]["latest_played_at"], str)

    assert rows_by_source["chesscom"]["games_played"] == 81
    assert rows_by_source["chesscom"]["synced"] is True
    assert isinstance(rows_by_source["chesscom"]["latest_played_at"], str)


def test_dashboard_source_sync_reports_unsynced_when_no_recent_games() -> None:
    payload = _prepare_payload(
        rows=[
            ("chesscom", 34, 15, "c90"),
            ("lichess", 22, 120, "lold"),
        ],
    )
    source_sync = payload["source_sync"]
    rows_by_source = {row["source"]: row for row in source_sync["sources"]}

    assert rows_by_source["chesscom"]["games_played"] == 34
    assert rows_by_source["chesscom"]["synced"] is True

    assert rows_by_source["lichess"]["games_played"] == 0
    assert rows_by_source["lichess"]["synced"] is False
    assert rows_by_source["lichess"]["latest_played_at"] is None
