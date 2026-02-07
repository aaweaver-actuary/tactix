from __future__ import annotations

import importlib
import os
import shutil
import tempfile
from datetime import date
from io import StringIO
from pathlib import Path

import chess
import chess.pgn
import pytest
from fastapi.testclient import TestClient

from tactix._get_game_result_for_user_from_pgn_headers import (
    _get_game_result_for_user_from_pgn_headers,
)
from tactix._get_user_color_from_pgn_headers import _get_user_color_from_pgn_headers
from tactix.chess_game_result import ChessGameResult
from tactix.chess_player_color import ChessPlayerColor
from tactix.db.duckdb_store import get_connection

USER = "groborger"
SOURCE = "chesscom"
PROFILE = "bullet"
FIXTURE_NAME = "chesscom_2_bullet_games.pgn"
FIXTURE_DATE = date(2026, 2, 1)
TIME_CONTROL = "120+1"
DB_NAME = "tactix_feature_pipeline_validation_2026_02_01"


def _ensure_stockfish_available() -> None:
    if not shutil.which("stockfish"):
        pytest.skip("Stockfish binary not on PATH")


def _run_pipeline(tmp_dir: Path) -> Path:
    old_env = {
        "TACTIX_API_TOKEN": os.environ.get("TACTIX_API_TOKEN"),
        "TACTIX_DATA_DIR": os.environ.get("TACTIX_DATA_DIR"),
        "TACTIX_SOURCE": os.environ.get("TACTIX_SOURCE"),
    }
    os.environ["TACTIX_API_TOKEN"] = "test-token"
    os.environ["TACTIX_DATA_DIR"] = str(tmp_dir)
    os.environ["TACTIX_SOURCE"] = SOURCE

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
                "source": SOURCE,
                "profile": PROFILE,
                "user_id": USER,
                "start_date": "2026-02-01",
                "end_date": "2026-02-01",
                "use_fixture": "true",
                "fixture_name": FIXTURE_NAME,
                "db_name": DB_NAME,
                "reset_db": "true",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload.get("result", {}).get("fetched_games") == 2
        assert payload.get("counts", {}).get("games") == 2
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    return tmp_dir / f"{DB_NAME}.duckdb"


def _load_games(conn) -> list[tuple[str, chess.pgn.Game]]:
    rows = conn.execute(
        """
        SELECT game_id, pgn
        FROM games
        WHERE source = ?
        AND time_control = ?
        AND CAST(played_at AS DATE) BETWEEN ? AND ?
        ORDER BY game_id
        """,
        (SOURCE, TIME_CONTROL, FIXTURE_DATE, FIXTURE_DATE),
    ).fetchall()
    games: list[tuple[str, chess.pgn.Game]] = []
    for game_id, pgn_text in rows:
        game = chess.pgn.read_game(StringIO(pgn_text or ""))
        if game is None:
            raise AssertionError(f"Unable to parse PGN for game {game_id}")
        games.append((game_id, game))
    return games


def _rating_diff(headers: chess.pgn.Headers, user: str) -> int:
    white_elo = int(headers.get("WhiteElo") or 0)
    black_elo = int(headers.get("BlackElo") or 0)
    color = _get_user_color_from_pgn_headers(headers, user)
    if color == ChessPlayerColor.WHITE:
        return black_elo - white_elo
    return white_elo - black_elo


def _captured_piece_label(fen: str, best_uci: str) -> str | None:
    if not best_uci:
        return None
    board = chess.Board(fen)
    move = chess.Move.from_uci(best_uci)
    piece = board.piece_at(move.to_square) or board.piece_at(move.from_square)
    if not piece:
        return None
    if piece.piece_type == chess.KNIGHT:
        return "knight"
    if piece.piece_type == chess.BISHOP:
        return "bishop"
    return None


def _loss_game_id(games: list[tuple[str, chess.pgn.Game]]) -> str:
    for game_id, game in games:
        if (
            _get_game_result_for_user_from_pgn_headers(game.headers, USER)
            == ChessGameResult.LOSS
        ):
            return game_id
    raise AssertionError("Loss game not found in canonical fixture")


@pytest.fixture(scope="module")
def canonical_db_path() -> Path:
    _ensure_stockfish_available()
    tmp_dir = Path(tempfile.mkdtemp())
    return _run_pipeline(tmp_dir)


@pytest.fixture(scope="module")
def canonical_games(canonical_db_path: Path) -> list[tuple[str, chess.pgn.Game]]:
    conn = get_connection(canonical_db_path)
    try:
        games = _load_games(conn)
    finally:
        conn.close()
    if len(games) != 2:
        raise AssertionError(f"Expected 2 games, found {len(games)}")
    return games


def test_canonical_pipeline_ingests_two_games(canonical_games) -> None:
    assert len(canonical_games) == 2


def test_canonical_pipeline_results_include_win_and_loss(canonical_games) -> None:
    results = {
        _get_game_result_for_user_from_pgn_headers(game.headers, USER)
        for _, game in canonical_games
    }
    assert results == {ChessGameResult.WIN, ChessGameResult.LOSS}


def test_canonical_pipeline_rating_deltas(canonical_games) -> None:
    loss_game = next(
        game for _, game in canonical_games
        if _get_game_result_for_user_from_pgn_headers(game.headers, USER) == ChessGameResult.LOSS
    )
    win_game = next(
        game for _, game in canonical_games
        if _get_game_result_for_user_from_pgn_headers(game.headers, USER) == ChessGameResult.WIN
    )
    assert _rating_diff(loss_game.headers, USER) > 50
    assert _rating_diff(win_game.headers, USER) <= 50


def test_canonical_pipeline_missed_hanging_pieces(
    canonical_db_path: Path,
    canonical_games,
) -> None:
    conn = get_connection(canonical_db_path)
    try:
        loss_game_id = _loss_game_id(canonical_games)
        tactic_rows = conn.execute(
            """
            SELECT t.tactic_id, t.position_id, t.best_uci, p.fen
            FROM tactics t
            JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
            JOIN positions p ON p.position_id = t.position_id
            WHERE t.game_id = ?
            AND t.motif = 'hanging_piece'
            AND o.result = 'missed'
            """,
            [loss_game_id],
        ).fetchall()
    finally:
        conn.close()

    labels = {
        label
        for _, _, best_uci, fen in tactic_rows
        if (label := _captured_piece_label(fen, best_uci)) is not None
    }
    assert labels == {"knight", "bishop"}


def test_canonical_pipeline_pre_blunder_positions_recorded(
    canonical_db_path: Path,
    canonical_games,
) -> None:
    conn = get_connection(canonical_db_path)
    try:
        loss_game_id = _loss_game_id(canonical_games)
        tactic_rows = conn.execute(
            """
            SELECT t.tactic_id, t.position_id, t.best_uci, p.fen
            FROM tactics t
            JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
            JOIN positions p ON p.position_id = t.position_id
            WHERE t.game_id = ?
            AND t.motif = 'hanging_piece'
            AND o.result = 'missed'
            """,
            [loss_game_id],
        ).fetchall()
        queue_rows = conn.execute(
            """
            SELECT opportunity_id, position_id, fen, result
            FROM practice_queue
            WHERE game_id = ?
            """,
            [loss_game_id],
        ).fetchall()
        queue_by_id = {row[0]: row for row in queue_rows}

        canonical: dict[str, tuple[int, int, str, str]] = {}
        for tactic_id, position_id, best_uci, fen in tactic_rows:
            label = _captured_piece_label(fen, best_uci)
            if label in {"knight", "bishop"} and label not in canonical:
                canonical[label] = (tactic_id, position_id, best_uci, fen)

        assert set(canonical.keys()) == {"knight", "bishop"}

        for _, (tactic_id, position_id, best_uci, fen) in canonical.items():
            queue_row = queue_by_id.get(tactic_id)
            assert queue_row is not None
            assert queue_row[1] == position_id
            assert queue_row[2] == fen
            assert queue_row[3] == "missed"

            position_row = conn.execute(
                """
                SELECT fen, user_to_move
                FROM positions
                WHERE position_id = ?
                """,
                [position_id],
            ).fetchone()
            assert position_row is not None
            assert position_row[0] == fen
            assert position_row[1] is True

            move_row = conn.execute(
                """
                SELECT played_uci
                FROM user_moves
                WHERE position_id = ?
                """,
                [position_id],
            ).fetchone()
            assert move_row is not None
            assert move_row[0] != best_uci
    finally:
        conn.close()


def test_canonical_pipeline_results_persisted(canonical_db_path: Path) -> None:
    conn = get_connection(canonical_db_path)
    try:
        counts = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM games WHERE source = ?) AS games,
                (SELECT COUNT(*) FROM positions WHERE source = ?) AS positions,
                (SELECT COUNT(*) FROM tactics WHERE game_id IN (
                    SELECT game_id FROM games WHERE source = ?
                )) AS tactics,
                (SELECT COUNT(*) FROM tactic_outcomes) AS outcomes,
                (SELECT COUNT(*) FROM practice_queue WHERE source = ?) AS practice_queue
            """,
            (SOURCE, SOURCE, SOURCE, SOURCE),
        ).fetchone()
    finally:
        conn.close()

    games, positions, tactics, outcomes, practice_queue = counts
    assert games == 2
    assert positions > 0
    assert tactics > 0
    assert outcomes > 0
    assert practice_queue > 0
