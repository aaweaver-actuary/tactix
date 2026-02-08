import importlib
import os
import shutil
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tactix.db.duckdb_store import get_connection
from tactix.extract_game_id import extract_game_id
from tactix.extract_last_timestamp_ms import extract_last_timestamp_ms
from tactix.infra.clients.lichess_client import LichessClient, build_cursor
from tactix.pgn_utils import split_pgn_chunks


def _ensure_stockfish_available() -> None:
    if not shutil.which("stockfish"):
        pytest.skip("Stockfish binary not on PATH")


def _build_cursor_expectations(
    rows: list[dict[str, object]],
) -> tuple[str, set[str], int, str]:
    ordered = sorted(
        rows,
        key=lambda row: (int(row["last_timestamp_ms"]), str(row["game_id"])),
    )
    cursor_row = ordered[0]
    cursor = build_cursor(
        int(cursor_row["last_timestamp_ms"]),
        str(cursor_row["game_id"]),
    )
    cursor_tuple = (
        int(cursor_row["last_timestamp_ms"]),
        str(cursor_row["game_id"]),
    )
    expected_ids = {
        str(row["game_id"])
        for row in ordered
        if (int(row["last_timestamp_ms"]), str(row["game_id"])) > cursor_tuple
    }
    expected_since_ms = int(cursor_row["last_timestamp_ms"])
    expected_next_cursor = build_cursor(
        int(ordered[-1]["last_timestamp_ms"]),
        str(ordered[-1]["game_id"]),
    )
    return cursor, expected_ids, expected_since_ms, expected_next_cursor


def _fetch_game_ids(conn, start_date: date, end_date: date) -> set[str]:
    rows = conn.execute(
        """
        SELECT g.game_id
        FROM games g
        WHERE g.source = ?
        AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
        """,
        ("lichess", start_date, end_date),
    ).fetchall()
    return {row[0] for row in rows}


def _fetch_raw_pgn_count(conn) -> int:
    return int(
        conn.execute(
            "SELECT COUNT(*) FROM raw_pgns WHERE source = ?",
            ("lichess",),
        ).fetchone()[0]
    )


def test_api_pipeline_lichess_cursor_incremental_sync() -> None:  # noqa: PLR0915
    _ensure_stockfish_available()

    tmp_dir = Path(tempfile.mkdtemp())
    db_name = "tactix_feature_lichess_cursor_incremental"

    old_env = {
        "TACTIX_API_TOKEN": os.environ.get("TACTIX_API_TOKEN"),
        "TACTIX_DATA_DIR": os.environ.get("TACTIX_DATA_DIR"),
        "TACTIX_SOURCE": os.environ.get("TACTIX_SOURCE"),
    }

    os.environ["TACTIX_API_TOKEN"] = "test-token"  # noqa: S105
    os.environ["TACTIX_DATA_DIR"] = str(tmp_dir)
    os.environ["TACTIX_SOURCE"] = "lichess"

    fixture_name = "lichess_rapid_sample.pgn"
    fixture_path = Path(__file__).resolve().parent / "fixtures" / fixture_name
    chunks = split_pgn_chunks(fixture_path.read_text())
    fixture_rows = [
        {
            "game_id": extract_game_id(chunk),
            "last_timestamp_ms": extract_last_timestamp_ms(chunk),
        }
        for chunk in chunks
    ]
    cursor, expected_ids, expected_since_ms, expected_next_cursor = (
        _build_cursor_expectations(fixture_rows)
    )
    assert expected_ids

    try:
        import tactix.api as api_module
        import tactix.config as config_module

        importlib.reload(config_module)
        importlib.reload(api_module)

        settings = config_module.get_settings(source="lichess", profile="rapid")
        settings.checkpoint_path.write_text(cursor)

        client = TestClient(api_module.app)
        params = {
            "source": "lichess",
            "profile": "rapid",
            "user_id": "lichess",
            "start_date": "2024-06-01",
            "end_date": "2024-06-03",
            "use_fixture": "true",
            "fixture_name": fixture_name,
            "db_name": db_name,
            "reset_db": "true",
        }

        captured_requests = []
        original_fetch = LichessClient.fetch_incremental_games

        def _capture_fetch(self, request):
            captured_requests.append(request)
            return original_fetch(self, request)

        with patch.object(LichessClient, "fetch_incremental_games", _capture_fetch):
            response_first = client.post(
                "/api/pipeline/run",
                headers={"Authorization": "Bearer test-token"},
                params=params,
            )

        assert response_first.status_code == 200
        payload = response_first.json()
        result = payload.get("result") or {}
        counts = payload.get("counts") or {}

        assert captured_requests
        assert captured_requests[-1].cursor == cursor
        assert captured_requests[-1].since_ms == expected_since_ms

        assert result.get("fetched_games") == len(expected_ids)
        assert counts.get("games") == len(expected_ids)

        db_path = tmp_dir / f"{db_name}.duckdb"
        conn = get_connection(db_path)
        try:
            game_ids = _fetch_game_ids(conn, date(2024, 6, 1), date(2024, 6, 3))
            raw_pgn_count = _fetch_raw_pgn_count(conn)
        finally:
            conn.close()

        assert game_ids == expected_ids
        assert settings.checkpoint_path.read_text().strip() == expected_next_cursor

        response_second = client.post(
            "/api/pipeline/run",
            headers={"Authorization": "Bearer test-token"},
            params={**params, "reset_db": "false"},
        )
        assert response_second.status_code == 200
        second_result = response_second.json().get("result") or {}
        assert second_result.get("fetched_games") == 0

        conn = get_connection(db_path)
        try:
            game_ids_second = _fetch_game_ids(conn, date(2024, 6, 1), date(2024, 6, 3))
            raw_pgn_count_second = _fetch_raw_pgn_count(conn)
        finally:
            conn.close()

        assert game_ids_second == game_ids
        assert raw_pgn_count_second == raw_pgn_count
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
