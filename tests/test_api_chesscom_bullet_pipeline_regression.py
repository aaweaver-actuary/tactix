import importlib
import os
import shutil
import tempfile
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tactix.dashboard_query import DashboardQuery
from tactix.db.dashboard_repository_provider import fetch_opportunity_motif_counts
from tactix.db.duckdb_store import get_connection, init_schema


def _ensure_stockfish_available() -> None:
    if not shutil.which("stockfish"):
        pytest.skip("Stockfish binary not on PATH")


def _query_count(
    conn,
    sql: str,
    params: tuple[object, ...],
) -> int:
    return int(conn.execute(sql, params).fetchone()[0])


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
