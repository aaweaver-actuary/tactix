import importlib
import os
import shutil
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tactix.dashboard_query import DashboardQuery
from tactix.db.dashboard_repository_provider import fetch_opportunity_motif_counts
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.infra.clients.chesscom_client import (
    ChesscomClient,
    _build_cursor,
    _filter_by_cursor,
    _parse_cursor,
)
from tactix.pgn_utils import extract_game_id, extract_last_timestamp_ms, split_pgn_chunks


def _ensure_stockfish_available() -> None:
    if not shutil.which("stockfish"):
        pytest.skip("Stockfish binary not on PATH")


def _query_count(
    conn,
    sql: str,
    params: tuple[object, ...],
) -> int:
    return int(conn.execute(sql, params).fetchone()[0])


def _snapshot_idempotency_state(
    conn,
    source: str,
    start_date: date,
    end_date: date,
) -> dict[str, object]:
    init_schema(conn)
    counts = {
        "raw_pgns": _query_count(
            conn,
            """
            SELECT COUNT(*)
            FROM raw_pgns r
            WHERE r.source = ?
            """,
            (source,),
        ),
        "games": _query_count(
            conn,
            """
            SELECT COUNT(*)
            FROM games g
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ),
        "positions": _query_count(
            conn,
            """
            SELECT COUNT(*)
            FROM positions p
            JOIN games g ON g.game_id = p.game_id AND g.source = p.source
            WHERE p.user_to_move IS TRUE
            AND g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ),
        "user_moves": _query_count(
            conn,
            """
            SELECT COUNT(*)
            FROM user_moves u
            JOIN games g ON g.game_id = u.game_id AND g.source = u.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ),
        "opportunities": _query_count(
            conn,
            """
            SELECT COUNT(*)
            FROM opportunities o
            JOIN games g ON g.game_id = o.game_id AND g.source = o.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ),
        "conversions": _query_count(
            conn,
            """
            SELECT COUNT(*)
            FROM conversions c
            JOIN games g ON g.game_id = c.game_id AND g.source = c.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ),
        "practice_queue": _query_count(
            conn,
            """
            SELECT COUNT(*)
            FROM practice_queue q
            JOIN games g ON g.game_id = q.game_id AND g.source = q.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ),
    }
    game_ids = {
        row[0]
        for row in conn.execute(
            """
            SELECT DISTINCT g.game_id
            FROM games g
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            ORDER BY g.game_id
            """,
            (source, start_date, end_date),
        ).fetchall()
    }
    position_keys = {
        (row[0], row[1])
        for row in conn.execute(
            """
            SELECT p.game_id, p.ply
            FROM positions p
            JOIN games g ON g.game_id = p.game_id AND g.source = p.source
            WHERE p.user_to_move IS TRUE
            AND g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ).fetchall()
    }
    move_keys = {
        row[0]
        for row in conn.execute(
            """
            SELECT u.position_id
            FROM user_moves u
            JOIN games g ON g.game_id = u.game_id AND g.source = u.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ).fetchall()
    }
    opportunity_keys = {
        (row[0], row[1], row[2] or "")
        for row in conn.execute(
            """
            SELECT o.position_id, o.motif, o.best_uci
            FROM opportunities o
            JOIN games g ON g.game_id = o.game_id AND g.source = o.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ).fetchall()
    }
    conversion_keys = {
        (row[0], row[1] or "", row[2] or "")
        for row in conn.execute(
            """
            SELECT c.opportunity_id, c.result, c.user_uci
            FROM conversions c
            JOIN games g ON g.game_id = c.game_id AND g.source = c.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ).fetchall()
    }
    practice_keys = {
        (row[0], row[1])
        for row in conn.execute(
            """
            SELECT q.opportunity_id, q.position_id
            FROM practice_queue q
            JOIN games g ON g.game_id = q.game_id AND g.source = q.source
            WHERE g.source = ?
            AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
            """,
            (source, start_date, end_date),
        ).fetchall()
    }
    raw_pgn_keys = {
        (row[0], row[1] or "", int(row[2] or 0))
        for row in conn.execute(
            """
            SELECT r.game_id, r.pgn_hash, r.pgn_version
            FROM raw_pgns r
            WHERE r.source = ?
            """,
            (source,),
        ).fetchall()
    }
    return {
        "counts": counts,
        "game_ids": game_ids,
        "position_keys": position_keys,
        "move_keys": move_keys,
        "opportunity_keys": opportunity_keys,
        "conversion_keys": conversion_keys,
        "practice_keys": practice_keys,
        "raw_pgn_keys": raw_pgn_keys,
    }


def test_api_pipeline_chesscom_bullet_fixture_regression() -> None:
    _ensure_stockfish_available()

    tmp_dir = Path(tempfile.mkdtemp())
    db_name = "tactix_feature_001_chesscom_bullet_combined"

    old_env = {
        "TACTIX_API_TOKEN": os.environ.get("TACTIX_API_TOKEN"),
        "TACTIX_DATA_DIR": os.environ.get("TACTIX_DATA_DIR"),
        "TACTIX_SOURCE": os.environ.get("TACTIX_SOURCE"),
    }

    os.environ["TACTIX_API_TOKEN"] = "test-token"
    os.environ["TACTIX_DATA_DIR"] = str(tmp_dir)
    os.environ["TACTIX_SOURCE"] = "chesscom"

    try:
        import tactix.api as api_module
        import tactix.config as config_module

        importlib.reload(config_module)
        importlib.reload(api_module)

        client = TestClient(api_module.app)
        response = client.post(
            "/api/pipeline/run",
            headers={"Authorization": "Bearer test-token"},
            params={
                "source": "chesscom",
                "profile": "bullet",
                "user_id": "groborger",
                "start_date": "2026-02-01",
                "end_date": "2026-02-01",
                "use_fixture": "true",
                "fixture_name": "chesscom_bullet_mate_hanging_2026_02_01.pgn",
                "db_name": db_name,
                "reset_db": "true",
            },
        )
        assert response.status_code == 200

        payload = response.json()
        result = payload.get("result") or {}
        counts = payload.get("counts") or {}

        assert result.get("fetched_games", 0) > 0
        assert counts.get("games", 0) > 0
        assert counts.get("positions", 0) > 0
        assert counts.get("user_moves", 0) > 0
        assert counts.get("opportunities", 0) > 0
        assert counts.get("conversions", 0) > 0
        assert counts.get("practice_queue", 0) > 0
        assert counts.get("positions") == counts.get("user_moves")

        db_path = tmp_dir / f"{db_name}.duckdb"
        conn = get_connection(db_path)
        try:
            init_schema(conn)
            start_date = date(2026, 2, 1)
            end_date = date(2026, 2, 1)

            games_count = _query_count(
                conn,
                """
                SELECT COUNT(*)
                FROM games g
                WHERE g.source = ?
                AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
                """,
                ("chesscom", start_date, end_date),
            )
            assert games_count > 0

            positions_count = _query_count(
                conn,
                """
                SELECT COUNT(*)
                FROM positions p
                JOIN games g ON g.game_id = p.game_id AND g.source = p.source
                WHERE p.user_to_move IS TRUE
                AND g.source = ?
                AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
                """,
                ("chesscom", start_date, end_date),
            )
            assert positions_count > 0

            moves_count = _query_count(
                conn,
                """
                SELECT COUNT(*)
                FROM user_moves u
                JOIN games g ON g.game_id = u.game_id AND g.source = u.source
                WHERE g.source = ?
                AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
                """,
                ("chesscom", start_date, end_date),
            )
            assert moves_count == positions_count

            opportunities_count = _query_count(
                conn,
                """
                SELECT COUNT(*)
                FROM opportunities o
                JOIN games g ON g.game_id = o.game_id AND g.source = o.source
                WHERE g.source = ?
                AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
                """,
                ("chesscom", start_date, end_date),
            )
            assert opportunities_count > 0

            conversions_count = _query_count(
                conn,
                """
                SELECT COUNT(*)
                FROM conversions c
                JOIN games g ON g.game_id = c.game_id AND g.source = c.source
                WHERE g.source = ?
                AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
                """,
                ("chesscom", start_date, end_date),
            )
            assert conversions_count > 0
            assert conversions_count == opportunities_count

            practice_queue_count = _query_count(
                conn,
                """
                SELECT COUNT(*)
                FROM practice_queue q
                JOIN games g ON g.game_id = q.game_id AND g.source = q.source
                WHERE g.source = ?
                AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
                """,
                ("chesscom", start_date, end_date),
            )
            assert practice_queue_count > 0

            motif_totals = fetch_opportunity_motif_counts(
                conn,
                DashboardQuery(
                    source="chesscom",
                    start_date=start_date,
                    end_date=end_date,
                ),
            )
            assert motif_totals.get("hanging_piece", 0) > 0
            assert motif_totals.get("mate", 0) > 0
        finally:
            conn.close()

        summary_response = client.get(
            "/api/dashboard/summary",
            headers={"Authorization": "Bearer test-token"},
            params={
                "source": "chesscom",
                "start_date": "2026-02-01",
                "end_date": "2026-02-01",
                "db_name": db_name,
            },
        )
        assert summary_response.status_code == 200
        summary = summary_response.json().get("summary") or {}

        assert summary.get("games") == games_count
        assert summary.get("positions") == positions_count
        assert summary.get("user_moves") == moves_count
        assert summary.get("opportunities") == opportunities_count
        assert summary.get("conversions") == conversions_count
        assert summary.get("practice_queue") == practice_queue_count
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_api_pipeline_chesscom_bullet_idempotency() -> None:
    _ensure_stockfish_available()

    tmp_dir = Path(tempfile.mkdtemp())
    db_name = "tactix_feature_008_chesscom_bullet_idempotent"

    old_env = {
        "TACTIX_API_TOKEN": os.environ.get("TACTIX_API_TOKEN"),
        "TACTIX_DATA_DIR": os.environ.get("TACTIX_DATA_DIR"),
        "TACTIX_SOURCE": os.environ.get("TACTIX_SOURCE"),
    }

    os.environ["TACTIX_API_TOKEN"] = "test-token"
    os.environ["TACTIX_DATA_DIR"] = str(tmp_dir)
    os.environ["TACTIX_SOURCE"] = "chesscom"

    try:
        import tactix.api as api_module
        import tactix.config as config_module

        importlib.reload(config_module)
        importlib.reload(api_module)

        client = TestClient(api_module.app)
        params = {
            "source": "chesscom",
            "profile": "bullet",
            "user_id": "groborger",
            "start_date": "2026-02-01",
            "end_date": "2026-02-01",
            "use_fixture": "true",
            "fixture_name": "chesscom_bullet_mate_hanging_2026_02_01.pgn",
            "db_name": db_name,
            "reset_db": "true",
        }

        response_first = client.post(
            "/api/pipeline/run",
            headers={"Authorization": "Bearer test-token"},
            params=params,
        )
        assert response_first.status_code == 200

        db_path = tmp_dir / f"{db_name}.duckdb"
        conn = get_connection(db_path)
        try:
            snapshot_first = _snapshot_idempotency_state(
                conn,
                "chesscom",
                date(2026, 2, 1),
                date(2026, 2, 1),
            )
        finally:
            conn.close()

        params_second = {**params, "reset_db": "false"}
        response_second = client.post(
            "/api/pipeline/run",
            headers={"Authorization": "Bearer test-token"},
            params=params_second,
        )
        assert response_second.status_code == 200

        conn = get_connection(db_path)
        try:
            snapshot_second = _snapshot_idempotency_state(
                conn,
                "chesscom",
                date(2026, 2, 1),
                date(2026, 2, 1),
            )
        finally:
            conn.close()

        assert snapshot_second["counts"] == snapshot_first["counts"]
        assert snapshot_second["game_ids"] == snapshot_first["game_ids"]
        assert snapshot_second["position_keys"] == snapshot_first["position_keys"]
        assert snapshot_second["move_keys"] == snapshot_first["move_keys"]
        assert snapshot_second["opportunity_keys"] == snapshot_first["opportunity_keys"]
        assert snapshot_second["conversion_keys"] == snapshot_first["conversion_keys"]
        assert snapshot_second["practice_keys"] == snapshot_first["practice_keys"]
        assert snapshot_second["raw_pgn_keys"] == snapshot_first["raw_pgn_keys"]

        counts = snapshot_second["counts"]
        assert counts["positions"] == counts["user_moves"]
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_api_pipeline_chesscom_cursor_incremental_sync() -> None:
    _ensure_stockfish_available()

    tmp_dir = Path(tempfile.mkdtemp())
    db_name = "tactix_feature_chesscom_cursor_incremental"

    old_env = {
        "TACTIX_API_TOKEN": os.environ.get("TACTIX_API_TOKEN"),
        "TACTIX_DATA_DIR": os.environ.get("TACTIX_DATA_DIR"),
        "TACTIX_SOURCE": os.environ.get("TACTIX_SOURCE"),
    }

    os.environ["TACTIX_API_TOKEN"] = "test-token"
    os.environ["TACTIX_DATA_DIR"] = str(tmp_dir)
    os.environ["TACTIX_SOURCE"] = "chesscom"

    fixture_name = "chesscom_bullet_mate_hanging_2026_02_01.pgn"
    fixture_path = Path(__file__).resolve().parent / "fixtures" / fixture_name
    chunks = split_pgn_chunks(fixture_path.read_text())
    fixture_rows = [
        {
            "game_id": extract_game_id(chunk),
            "last_timestamp_ms": extract_last_timestamp_ms(chunk),
        }
        for chunk in chunks
    ]
    ordered_rows = list(fixture_rows)
    ordered_rows.sort(key=lambda row: int(row.get("last_timestamp_ms", 0)))
    cursor_row = ordered_rows[0]
    cursor = _build_cursor(
        int(cursor_row["last_timestamp_ms"]),
        str(cursor_row["game_id"]),
    )
    filtered_rows = _filter_by_cursor(list(fixture_rows), cursor)
    expected_ids = {row["game_id"] for row in filtered_rows}
    assert expected_ids

    expected_since_ms, _ = _parse_cursor(cursor)
    expected_next_cursor = None
    if filtered_rows:
        newest = max(
            filtered_rows,
            key=lambda row: int(row.get("last_timestamp_ms", 0)),
        )
        expected_next_cursor = _build_cursor(
            int(newest.get("last_timestamp_ms", 0)),
            str(newest.get("game_id", "")),
        )

    try:
        import tactix.api as api_module
        import tactix.config as config_module

        importlib.reload(config_module)
        importlib.reload(api_module)

        settings = config_module.get_settings(source="chesscom", profile="bullet")
        settings.checkpoint_path.write_text(cursor)

        client = TestClient(api_module.app)
        params = {
            "source": "chesscom",
            "profile": "bullet",
            "user_id": "groborger",
            "use_fixture": "true",
            "fixture_name": fixture_name,
            "db_name": db_name,
            "reset_db": "true",
        }

        captured_requests = []
        original_fetch = ChesscomClient.fetch_incremental_games

        def _capture_fetch(self, request):
            captured_requests.append(request)
            return original_fetch(self, request)

        with patch.object(ChesscomClient, "fetch_incremental_games", _capture_fetch):
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
            game_ids = {
                row[0]
                for row in conn.execute(
                    """
                    SELECT g.game_id
                    FROM games g
                    WHERE g.source = ?
                    AND CAST(g.played_at AS DATE) BETWEEN ? AND ?
                    """,
                    ("chesscom", date(2026, 2, 1), date(2026, 2, 1)),
                ).fetchall()
            }
        finally:
            conn.close()

        assert game_ids == expected_ids
        assert settings.checkpoint_path.read_text().strip() == expected_next_cursor

        conn = get_connection(db_path)
        try:
            snapshot_first = _snapshot_idempotency_state(
                conn,
                "chesscom",
                date(2026, 2, 1),
                date(2026, 2, 1),
            )
        finally:
            conn.close()

        params_second = {**params, "reset_db": "false"}
        response_second = client.post(
            "/api/pipeline/run",
            headers={"Authorization": "Bearer test-token"},
            params=params_second,
        )
        assert response_second.status_code == 200
        second_result = response_second.json().get("result") or {}
        assert second_result.get("fetched_games") == 0

        conn = get_connection(db_path)
        try:
            snapshot_second = _snapshot_idempotency_state(
                conn,
                "chesscom",
                date(2026, 2, 1),
                date(2026, 2, 1),
            )
        finally:
            conn.close()

        assert snapshot_second["counts"] == snapshot_first["counts"]
        assert snapshot_second["game_ids"] == snapshot_first["game_ids"]
        assert snapshot_second["position_keys"] == snapshot_first["position_keys"]
        assert snapshot_second["move_keys"] == snapshot_first["move_keys"]
        assert snapshot_second["opportunity_keys"] == snapshot_first["opportunity_keys"]
        assert snapshot_second["conversion_keys"] == snapshot_first["conversion_keys"]
        assert snapshot_second["practice_keys"] == snapshot_first["practice_keys"]
        assert snapshot_second["raw_pgn_keys"] == snapshot_first["raw_pgn_keys"]
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
