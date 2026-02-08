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
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.chess_game_result import ChessGameResult
from tactix.chess_player_color import ChessPlayerColor

USER = "groborger"
SOURCE = "chesscom"
PROFILE = "bullet"
FIXTURE_NAME = "chesscom_2_bullet_games.pgn"
FIXTURE_DATE = date(2026, 2, 1)
DB_NAME = "tactix_feature_api_verification_2026_02_01"
AUTH_HEADERS = {"Authorization": "Bearer test-token"}


def _ensure_stockfish_available() -> None:
    if not shutil.which("stockfish"):
        pytest.skip("Stockfish binary not on PATH")


def _capture_square(board: chess.Board, move: chess.Move) -> chess.Square:
    if board.is_en_passant(move):
        return move.to_square + (-8 if board.turn == chess.WHITE else 8)
    return move.to_square


def _hanging_user_piece_labels_after_move(fen: str, user_move_uci: str) -> set[str]:
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


def _rating_diff(headers: chess.pgn.Headers, user: str) -> int:
    white_elo = int(headers.get("WhiteElo") or 0)
    black_elo = int(headers.get("BlackElo") or 0)
    color = _get_user_color_from_pgn_headers(headers, user)
    if color == ChessPlayerColor.WHITE:
        return black_elo - white_elo
    return white_elo - black_elo


def _game_headers_from_detail(payload: dict[str, object]) -> chess.pgn.Headers:
    pgn = payload.get("pgn")
    if not isinstance(pgn, str):
        raise AssertionError("Expected PGN string in game detail payload")
    game = chess.pgn.read_game(StringIO(pgn))
    if game is None:
        raise AssertionError("Unable to parse PGN from game detail payload")
    return game.headers


@pytest.fixture(scope="module")
def canonical_client() -> TestClient:
    _ensure_stockfish_available()

    tmp_dir = Path(tempfile.mkdtemp())
    db_path = tmp_dir / f"{DB_NAME}.duckdb"
    old_env = {
        "TACTIX_API_TOKEN": os.environ.get("TACTIX_API_TOKEN"),
        "TACTIX_DATA_DIR": os.environ.get("TACTIX_DATA_DIR"),
        "TACTIX_DUCKDB_PATH": os.environ.get("TACTIX_DUCKDB_PATH"),
        "TACTIX_SOURCE": os.environ.get("TACTIX_SOURCE"),
    }
    os.environ["TACTIX_API_TOKEN"] = "test-token"
    os.environ["TACTIX_DATA_DIR"] = str(tmp_dir)
    os.environ["TACTIX_DUCKDB_PATH"] = str(db_path)
    os.environ["TACTIX_SOURCE"] = SOURCE

    try:
        import tactix.api as api_module
        import tactix.config as config_module
        import tactix.manage_lifespan__fastapi as lifespan_module

        importlib.reload(config_module)
        importlib.reload(api_module)

        lifespan_module._refresh_dashboard_cache_async = lambda _sources: None

        with TestClient(api_module.app) as client:
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
            yield client
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _fetch_recent_games(client: TestClient) -> list[dict[str, object]]:
    response = client.get(
        "/api/dashboard",
        params={
            "source": SOURCE,
            "time_control": "bullet",
            "start_date": FIXTURE_DATE.isoformat(),
            "end_date": FIXTURE_DATE.isoformat(),
        },
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    games = payload.get("recent_games")
    if not isinstance(games, list):
        raise AssertionError("Expected recent_games to be a list")
    return games


def _fetch_game_detail(client: TestClient, game_id: str) -> dict[str, object]:
    response = client.get(
        f"/api/games/{game_id}",
        params={"source": SOURCE},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    if not isinstance(payload, dict):
        raise AssertionError("Expected game detail payload to be a dict")
    return payload


def _fetch_game_headers_by_id(
    client: TestClient, games: list[dict[str, object]]
) -> dict[str, chess.pgn.Headers]:
    headers_by_id: dict[str, chess.pgn.Headers] = {}
    for game in games:
        game_id = game.get("game_id")
        if not isinstance(game_id, str):
            raise AssertionError("Expected game_id string in dashboard payload")
        detail_payload = _fetch_game_detail(client, game_id)
        headers_by_id[game_id] = _game_headers_from_detail(detail_payload)
    return headers_by_id


def test_api_dashboard_returns_two_games(canonical_client: TestClient) -> None:
    games = _fetch_recent_games(canonical_client)
    assert len(games) == 2
    results = [game.get("result") for game in games]
    assert results.count("win") == 1
    assert results.count("loss") == 1


def test_api_game_detail_rating_deltas(canonical_client: TestClient) -> None:
    games = _fetch_recent_games(canonical_client)
    if len(games) != 2:
        raise AssertionError("Expected exactly two games from dashboard")

    headers_by_id = _fetch_game_headers_by_id(canonical_client, games)

    loss_headers = next(
        headers
        for headers in headers_by_id.values()
        if _get_game_result_for_user_from_pgn_headers(headers, USER) == ChessGameResult.LOSS
    )
    win_headers = next(
        headers
        for headers in headers_by_id.values()
        if _get_game_result_for_user_from_pgn_headers(headers, USER) == ChessGameResult.WIN
    )

    assert _rating_diff(loss_headers, USER) > 50
    assert _rating_diff(win_headers, USER) <= 50


def test_api_practice_queue_contains_hung_bishop_and_knight(
    canonical_client: TestClient,
) -> None:
    games = _fetch_recent_games(canonical_client)
    loss_game_id = next(game.get("game_id") for game in games if game.get("result") == "loss")
    if not isinstance(loss_game_id, str):
        raise AssertionError("Expected loss game_id string")

    response = canonical_client.get(
        "/api/practice/queue",
        params={
            "source": SOURCE,
            "limit": 50,
        },
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    items = payload.get("items")
    if not isinstance(items, list):
        raise AssertionError("Expected practice queue items list")

    loss_items = [item for item in items if item.get("game_id") == loss_game_id]
    assert len(loss_items) >= 2

    labels: set[str] = set()
    for item in loss_items:
        fen = item.get("fen")
        position_uci = item.get("position_uci")
        if not isinstance(fen, str) or not isinstance(position_uci, str):
            continue
        labels.update(_hanging_user_piece_labels_after_move(fen, position_uci))

    assert "knight" in labels
    assert "bishop" in labels
