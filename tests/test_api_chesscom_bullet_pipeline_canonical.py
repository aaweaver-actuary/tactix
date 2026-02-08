from __future__ import annotations

import importlib
import os
import shutil
import tempfile
from datetime import UTC, date, datetime
from io import StringIO
from pathlib import Path

import chess
import chess.pgn
import pytest
from fastapi.testclient import TestClient

from tactix._extract_metadata_from_headers import _extract_metadata_from_headers
from tactix._get_game_result_for_user_from_pgn_headers import (
    _get_game_result_for_user_from_pgn_headers,
)
from tactix._get_user_color_from_pgn_headers import _get_user_color_from_pgn_headers
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.chess_game_result import ChessGameResult
from tactix.chess_player_color import ChessPlayerColor
from tactix.db.duckdb_store import get_connection
from tactix.extract_last_timestamp_ms import extract_last_timestamp_ms

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


def _run_pipeline(tmp_dir: Path) -> Path:  # noqa: PLR0915
    old_env = {
        "TACTIX_API_TOKEN": os.environ.get("TACTIX_API_TOKEN"),
        "TACTIX_DATA_DIR": os.environ.get("TACTIX_DATA_DIR"),
        "TACTIX_SOURCE": os.environ.get("TACTIX_SOURCE"),
    }
    os.environ["TACTIX_API_TOKEN"] = "test-token"  # noqa: S105
    os.environ["TACTIX_DATA_DIR"] = str(tmp_dir)
    os.environ["TACTIX_SOURCE"] = SOURCE

    try:
        import tactix.api as api_module  # noqa: PLC0415
        import tactix.config as config_module  # noqa: PLC0415

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


def _fetch_canonical_game_rows(conn) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT
            game_id,
            source,
            time_control,
            played_at,
            user_id,
            user_color,
            user_rating,
            opp_rating,
            result,
            pgn
        FROM games
        WHERE source = ?
        AND time_control = ?
        AND CAST(played_at AS DATE) BETWEEN ? AND ?
        ORDER BY game_id
        """,
        (SOURCE, TIME_CONTROL, FIXTURE_DATE, FIXTURE_DATE),
    ).fetchall()
    return [
        {
            "game_id": row[0],
            "source": row[1],
            "time_control": row[2],
            "played_at": row[3],
            "user_id": row[4],
            "user_color": row[5],
            "user_rating": row[6],
            "opp_rating": row[7],
            "result": row[8],
            "pgn": row[9],
        }
        for row in rows
    ]


def _expected_game_metadata(
    headers: chess.pgn.Headers,
    user: str,
    pgn_text: str,
) -> dict[str, object]:
    metadata = _extract_metadata_from_headers(headers, user)
    color = _get_user_color_from_pgn_headers(headers, user)
    user_color = "white" if color == ChessPlayerColor.WHITE else "black"
    played_at_ms = metadata.get("start_timestamp_ms") or extract_last_timestamp_ms(pgn_text)
    played_at = datetime.fromtimestamp(int(played_at_ms) / 1000, tz=UTC).replace(
        tzinfo=None
    )
    if user_color == "white":
        opp_rating = metadata.get("black_elo")
    else:
        opp_rating = metadata.get("white_elo")
    return {
        "user_color": user_color,
        "user_rating": metadata.get("user_rating"),
        "opp_rating": opp_rating,
        "result": _get_game_result_for_user_from_pgn_headers(headers, user).value,
        "time_control": metadata.get("time_control"),
        "played_at": played_at,
    }


def _capture_square(board: chess.Board, move: chess.Move) -> chess.Square:
    if board.is_en_passant(move):
        return move.to_square + (-8 if board.turn == chess.WHITE else 8)
    return move.to_square


def _hanging_user_piece_labels_after_move(fen: str, user_move_uci: str) -> set[str]:  # noqa: PLR0912, PLR0915
    if not user_move_uci:
        return set()
    board = chess.Board(fen)
    move = chess.Move.from_uci(user_move_uci)
    if move not in board.legal_moves:
        return set()
    moved_piece = board.piece_at(move.from_square)
    user_color = board.turn
    board.push(move)
    if moved_piece is None:
        return set()
    target_square = move.to_square
    labels: set[str] = set()
    if board.is_attacked_by(not user_color, target_square):
        is_unprotected = not board.is_attacked_by(user_color, target_square)
        is_favorable = False
        for response in board.legal_moves:
            if not board.is_capture(response):
                continue
            capture_square = _capture_square(board, response)
            if capture_square != target_square:
                continue
            mover_piece = board.piece_at(response.from_square)
            if mover_piece is None:
                continue
            is_favorable = BaseTacticDetector.piece_value(
                moved_piece.piece_type
            ) > BaseTacticDetector.piece_value(mover_piece.piece_type)
            if is_favorable:
                break
        if is_unprotected or is_favorable:
            if moved_piece.piece_type == chess.KNIGHT:
                labels.add("knight")
            elif moved_piece.piece_type == chess.BISHOP:
                labels.add("bishop")
    return labels


def _loss_game_id(games: list[tuple[str, chess.pgn.Game]]) -> str:
    for game_id, game in games:
        if _get_game_result_for_user_from_pgn_headers(game.headers, USER) == ChessGameResult.LOSS:
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
        game
        for _, game in canonical_games
        if _get_game_result_for_user_from_pgn_headers(game.headers, USER) == ChessGameResult.LOSS
    )
    win_game = next(
        game
        for _, game in canonical_games
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
            SELECT t.tactic_id, t.position_id, t.best_uci, p.fen, p.uci
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

    labels: set[str] = set()
    for _, _, _best_uci, fen, user_move_uci in tactic_rows:
        labels.update(_hanging_user_piece_labels_after_move(fen, user_move_uci))
    assert {"knight", "bishop"}.issubset(labels)


def test_games_table_stores_canonical_metadata(canonical_db_path: Path) -> None:
    conn = get_connection(canonical_db_path)
    try:
        rows = _fetch_canonical_game_rows(conn)
    finally:
        conn.close()

    if len(rows) != 2:
        raise AssertionError(f"Expected 2 games rows, found {len(rows)}")

    for row in rows:
        pgn_text = row.get("pgn") or ""
        game = chess.pgn.read_game(StringIO(str(pgn_text)))
        if game is None:
            raise AssertionError(f"Unable to parse PGN for game {row.get('game_id')}")
        expected = _expected_game_metadata(game.headers, USER, str(pgn_text))

        assert row.get("source") == SOURCE
        assert row.get("user_id") == USER
        assert row.get("time_control") == expected["time_control"]
        assert row.get("user_color") == expected["user_color"]
        assert row.get("user_rating") == expected["user_rating"]
        assert row.get("opp_rating") == expected["opp_rating"]
        assert row.get("result") == expected["result"]
        assert row.get("played_at") == expected["played_at"]


def test_canonical_pipeline_pre_blunder_positions_recorded(
    canonical_db_path: Path,
    canonical_games,
) -> None:
    conn = get_connection(canonical_db_path)
    try:
        loss_game_id = _loss_game_id(canonical_games)
        tactic_rows = conn.execute(
            """
            SELECT t.tactic_id, t.position_id, t.best_uci, p.fen, p.uci
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
        for tactic_id, position_id, best_uci, fen, user_move_uci in tactic_rows:
            labels = _hanging_user_piece_labels_after_move(fen, user_move_uci)
            for label in labels:
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
