from unittest.mock import MagicMock, patch

from tactix.config import Settings
from tactix.sync_postgres_analysis_results__pipeline import _sync_postgres_analysis_results


def test_sync_postgres_analysis_results_returns_zero_without_pg() -> None:
    settings = Settings()
    assert _sync_postgres_analysis_results(MagicMock(), None, settings) == 0


def test_sync_postgres_analysis_results_upserts_rows() -> None:
    settings = Settings(source="chesscom")
    conn = MagicMock()
    pg_conn = MagicMock()
    rows = [
        {
            "game_id": "game-1",
            "position_id": 12,
            "motif": "hanging_piece",
            "severity": 1.5,
            "best_uci": "e2e4",
            "tactic_piece": "pawn",
            "mate_type": None,
            "best_san": "e4",
            "explanation": "test",
            "eval_cp": 40,
            "result": "missed",
            "user_uci": "e2e4",
            "eval_delta": -10,
        }
    ]
    pipeline_module = MagicMock()
    with (
        patch(
            "tactix.sync_postgres_analysis_results__pipeline.fetch_recent_tactics",
            return_value=rows,
        ),
        patch(
            "tactix.sync_postgres_analysis_results__pipeline.import_module",
            return_value=pipeline_module,
        ),
    ):
        synced = _sync_postgres_analysis_results(conn, pg_conn, settings, limit=1)

    pipeline_module.upsert_analysis_tactic_with_outcome.assert_called_once()
    assert synced == 1
