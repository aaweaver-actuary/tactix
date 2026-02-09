import shutil
import tempfile
from pathlib import Path

import pytest

from tactix.config import Settings
from tactix.db.duckdb_store import get_connection
from tactix.pipeline import run_daily_game_sync

USER = "groborger"
SOURCE = "chesscom"

EXPECTED_BY_GAME: dict[str, dict[str, str | bool | None]] = {
    "990000001": {
        "game_result": "win",
        "user_uci": "h3f2",
        "outcome_result": "found",
        "mate_found": True,
        "tactic_piece": "knight",
        "mate_type": "smothered",
    },
    "990000002": {
        "game_result": "loss",
        "user_uci": "c8e7",
        "outcome_result": "missed",
        "mate_found": False,
        "tactic_piece": "knight",
        "mate_type": "smothered",
    },
    "990000003": {
        "game_result": "win",
        "user_uci": "c8e7",
        "outcome_result": "missed",
        "mate_found": False,
        "tactic_piece": "knight",
        "mate_type": "smothered",
    },
}


def _fixture_path() -> Path:
    return (
        Path(__file__).resolve().parent
        / "fixtures"
        / "chesscom_bullet_mate_in_one_outcome_matrix.pgn"
    )


def _ensure_stockfish_available() -> None:
    if not shutil.which("stockfish"):
        pytest.skip("Stockfish binary not on PATH")


def _run_fixture_pipeline() -> Path:
    tmp_dir = Path(tempfile.mkdtemp())
    settings = Settings(
        source=SOURCE,
        user=USER,
        chesscom_user=USER,
        chesscom_profile="bullet",
        duckdb_path=tmp_dir / "mate_in_one_outcome_matrix.duckdb",
        checkpoint_path=tmp_dir / "chesscom_since.txt",
        metrics_version_file=tmp_dir / "metrics_version.txt",
        chesscom_fixture_pgn_path=_fixture_path(),
        chesscom_use_fixture_when_no_token=True,
        stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
        stockfish_movetime_ms=60,
        stockfish_depth=8,
        stockfish_multipv=1,
    )
    run_daily_game_sync(settings)
    return settings.duckdb_path


@pytest.fixture(scope="module")
def matrix_db_path() -> Path:
    _ensure_stockfish_available()
    return _run_fixture_pipeline()


def _fetch_mate_rows(
    conn,
) -> list[tuple[str, int, str, str, str, str, str, str, str, str]]:
    return conn.execute(
        """
        SELECT
            t.game_id,
            t.position_id,
            p.game_id,
            t.best_uci,
            o.result,
            o.user_uci,
            p.uci,
            t.tactic_piece,
            t.mate_type,
            g.result
        FROM tactics t
        JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
        JOIN positions p
            ON p.position_id = t.position_id
            AND p.game_id = t.game_id
        JOIN games g ON g.game_id = t.game_id
        WHERE t.motif = 'mate'
        ORDER BY t.game_id
        """
    ).fetchall()


def test_mate_in_one_fixture_has_expected_game_results(matrix_db_path: Path) -> None:
    conn = get_connection(matrix_db_path)
    try:
        rows = conn.execute("SELECT game_id, result FROM games ORDER BY game_id").fetchall()
    finally:
        conn.close()

    assert dict(rows) == {
        game_id: str(expected["game_result"]) for game_id, expected in EXPECTED_BY_GAME.items()
    }


def test_mate_in_one_rows_link_to_specific_game_and_position(matrix_db_path: Path) -> None:
    conn = get_connection(matrix_db_path)
    try:
        rows = _fetch_mate_rows(conn)
        position_ids = conn.execute(
            """
            SELECT position_id
            FROM positions
            WHERE game_id IN (?, ?, ?)
            AND COALESCE(user_to_move, TRUE) = TRUE
            """,
            list(EXPECTED_BY_GAME.keys()),
        ).fetchall()
    finally:
        conn.close()

    assert len(rows) == 3
    assert len(position_ids) == 3
    assert all(position_id is not None for (position_id,) in position_ids)
    for (
        game_id,
        position_id,
        position_game_id,
        _best_uci,
        _outcome_result,
        user_uci,
        position_uci,
        _tactic_piece,
        _mate_type,
        _game_result,
    ) in rows:
        assert game_id in EXPECTED_BY_GAME
        assert isinstance(position_id, int)
        assert position_id > 0
        assert game_id == position_game_id
        assert user_uci == position_uci


def test_mate_in_one_found_vs_not_found_status(matrix_db_path: Path) -> None:
    conn = get_connection(matrix_db_path)
    try:
        rows = _fetch_mate_rows(conn)
    finally:
        conn.close()

    observed = {}
    for (
        game_id,
        _position_id,
        _position_game_id,
        _best_uci,
        outcome_result,
        user_uci,
        _position_uci,
        tactic_piece,
        mate_type,
        _game_result,
    ) in rows:
        observed[game_id] = {
            "outcome_result": outcome_result,
            "user_uci": user_uci,
            "mate_found": outcome_result == "found",
            "tactic_piece": tactic_piece,
            "mate_type": mate_type,
        }

    for game_id, expected in EXPECTED_BY_GAME.items():
        assert observed[game_id]["outcome_result"] == expected["outcome_result"]
        assert observed[game_id]["user_uci"] == expected["user_uci"]
        assert observed[game_id]["mate_found"] == expected["mate_found"]
        assert observed[game_id]["tactic_piece"] == expected["tactic_piece"]
        assert observed[game_id]["mate_type"] == expected["mate_type"]


def test_mate_in_one_not_found_includes_won_and_lost_games(matrix_db_path: Path) -> None:
    conn = get_connection(matrix_db_path)
    try:
        rows = _fetch_mate_rows(conn)
    finally:
        conn.close()

    non_found_game_results = {
        game_result
        for (
            _game_id,
            _position_id,
            _position_game_id,
            _best_uci,
            outcome_result,
            _user_uci,
            _position_uci,
            _tactic_piece,
            _mate_type,
            game_result,
        ) in rows
        if outcome_result != "found"
    }
    assert non_found_game_results == {"win", "loss"}
