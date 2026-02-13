# Objective
# Verify that the data pipeline correctly ingests, classifies, and analyzes
# chess.com bullet games played on 2026-02-01, producing deterministic,
# reproducible results.

import shutil
import tempfile
from datetime import UTC, datetime, timezone
from pathlib import Path

import chess
import pytest

from tactix.config import Settings
from tactix.db.dashboard_repository_provider import fetch_recent_games
from tactix.db.duckdb_store import get_connection
from tactix.db.tactic_repository_provider import tactic_repository
from tactix.define_chess_game__chess_game import ChessGame
from tactix.pgn_utils import extract_last_timestamp_ms, split_pgn_chunks
from tactix.pipeline import run_daily_game_sync

USER = "groborger"
FIXTURE_DATE = "2026.02.01"
FIXTURE_TIME_CONTROL = "120+1"


def _fixture_path() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "chesscom_2_bullet_games.pgn"


def _ensure_stockfish_available() -> None:
    if not shutil.which("stockfish"):
        pytest.skip("Stockfish binary not on PATH")


def _run_fixture_pipeline() -> Path:
    tmp_dir = Path(tempfile.mkdtemp())
    settings = Settings(
        source="chesscom",
        user=USER,
        chesscom_user=USER,
        duckdb_path=tmp_dir / "tactix_chesscom_2026_02_01.duckdb",
        checkpoint_path=tmp_dir / "chesscom_since.txt",
        metrics_version_file=tmp_dir / "metrics_chesscom.txt",
        chesscom_fixture_pgn_path=_fixture_path(),
        chesscom_use_fixture_when_no_token=True,
        chesscom_profile="bullet",
        stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
        stockfish_movetime_ms=60,
        stockfish_depth=8,
        stockfish_multipv=2,
    )

    pgn_text = _fixture_path().read_text()
    timestamps = [extract_last_timestamp_ms(chunk) for chunk in split_pgn_chunks(pgn_text)]
    window_start = min(timestamps) - 1000
    window_end = max(timestamps) + 1000

    run_daily_game_sync(
        settings,
        window_start_ms=window_start,
        window_end_ms=window_end,
    )
    return settings.duckdb_path


def _load_games_from_db(db_path: Path) -> tuple[ChessGame, ChessGame]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT pgn FROM raw_pgns WHERE source = 'chesscom' ORDER BY raw_pgn_id"
        ).fetchall()
    finally:
        conn.close()
    games = [ChessGame(row[0]) for row in rows]
    if len(games) != 2:
        raise AssertionError(f"Expected 2 games, found {len(games)}")
    return games[0], games[1]


def _user_color(game: ChessGame, user: str) -> bool:
    headers = game.headers
    white = (headers.get("White") or "").lower()
    black = (headers.get("Black") or "").lower()
    if white == user.lower():
        return chess.WHITE
    if black == user.lower():
        return chess.BLACK
    raise AssertionError(f"User {user} not found in game headers")


def _result_for_user(game: ChessGame, user: str) -> str:
    headers = game.headers
    result = headers.get("Result")
    if result not in {"1-0", "0-1", "1/2-1/2"}:
        return "unknown"
    color = _user_color(game, user)
    if result == "1/2-1/2":
        return "draw"
    if color == chess.WHITE:
        return "win" if result == "1-0" else "loss"
    return "win" if result == "0-1" else "loss"


def _rating_diff(game: ChessGame, user: str) -> int:
    headers = game.headers
    white_elo = int(headers.get("WhiteElo") or 0)
    black_elo = int(headers.get("BlackElo") or 0)
    color = _user_color(game, user)
    if color == chess.WHITE:
        return black_elo - white_elo
    return white_elo - black_elo


def _base_seconds(time_control: str | None) -> int | None:
    if not time_control:
        return None
    token = time_control.split("+", maxsplit=1)[0]
    try:
        return int(token)
    except ValueError:
        return None


def _time_control_class(time_control: str | None) -> str:  # noqa: PLR0911
    base = _base_seconds(time_control)
    if base is None:
        return "unknown"
    if base <= 180:
        return "bullet"
    if base <= 600:
        return "blitz"
    if base <= 1800:
        return "rapid"
    if base <= 7200:
        return "classical"
    return "correspondence"


def _board_after_user_move(
    game: ChessGame, user: str, move_number: int
) -> tuple[chess.Board, chess.Move]:
    game_obj = game.game
    if game_obj is None:
        raise AssertionError("Unable to parse game")
    board = game_obj.board()
    user_color = _user_color(game, user)
    for node in game_obj.mainline():
        move = node.move
        if move is None:
            continue
        if board.turn == user_color and board.fullmove_number == move_number:
            board.push(move)
            return board, move
        board.push(move)
    raise AssertionError(f"Move {move_number} not found for user {user}")


def _game_for_result(games: tuple[ChessGame, ChessGame], user: str, result: str) -> ChessGame:
    return next(game for game in games if _result_for_user(game, user) == result)


def _board_after_user_move_for_result(
    games: tuple[ChessGame, ChessGame], user: str, result: str, move_number: int
) -> tuple[chess.Board, chess.Move]:
    game = _game_for_result(games, user, result)
    return _board_after_user_move(game, user, move_number)


def _is_attacked_by(
    board: chess.Board,
    square: chess.Square,
    attacker_color: bool,
    attacker_square: chess.Square,
) -> bool:
    return attacker_square in board.attackers(attacker_color, square)


@pytest.fixture(scope="module")
def pipeline_db_path() -> Path:
    """DuckDB path produced by the 2026-02-01 chess.com bullet fixture pipeline."""
    _ensure_stockfish_available()
    return _run_fixture_pipeline()


@pytest.fixture(scope="module")
def games_data(pipeline_db_path: Path) -> tuple[ChessGame, ChessGame]:
    """ChessGame objects:
    1. Extracted from Airflow pipeline for
    2. chess.com
    3. bullet games
    4. on 2026-02-01.

    Importantly, these games are identical to those in tests/fixtures/chesscom_2_bullet_games.pgn,
    but are obtained via the actual data pipeline to ensure end-to-end integrity.
    """
    return _load_games_from_db(pipeline_db_path)


def test_games_are_ingested_at_all(games_data):
    assert games_data


def test_exactly_two_bullet_games_ingested_for_2026_02_01_from_chess_dot_com(games_data):
    assert len(games_data) == 2
    sites = set()
    for game in games_data:
        headers = game.headers
        site = headers.get("Site") or ""
        assert "chess.com/game/live/" in site.lower()
        assert headers.get("Date") == FIXTURE_DATE
        assert headers.get("TimeControl") == FIXTURE_TIME_CONTROL
        sites.add(site)
    assert len(sites) == 2


def test_one_game_won_and_one_lost(games_data):
    results = {_result_for_user(game, USER) for game in games_data}
    assert results == {"win", "loss"}


def test_both_games_classified_as_bullet(games_data):
    for game in games_data:
        time_control = game.headers.get("TimeControl")
        assert _time_control_class(time_control) == "bullet"


def test_game_lost_had_rating_diff_gt_50(games_data):
    loss_game = _game_for_result(games_data, USER, "loss")
    assert _rating_diff(loss_game, USER) > 50


def test_game_won_had_rating_diff_lt_20(games_data):
    win_game = _game_for_result(games_data, USER, "win")
    assert _rating_diff(win_game, USER) <= 50


def test_user_played_one_white_and_one_black(games_data):
    colors = {_user_color(game, USER) for game in games_data}
    assert colors == {chess.WHITE, chess.BLACK}


def test_losing_game_user_left_knight_hanging_on_move_6(games_data):
    board, _move = _board_after_user_move_for_result(games_data, USER, "loss", 6)
    assert _is_attacked_by(board, chess.C6, chess.WHITE, chess.D5)


def test_losing_game_move_6_knight_on_c6(games_data):
    board, _move = _board_after_user_move_for_result(games_data, USER, "loss", 6)
    piece = board.piece_at(chess.C6)
    assert piece is not None
    assert piece.color == chess.BLACK
    assert piece.piece_type == chess.KNIGHT


def test_losing_game_user_played_6_e4_hanging_a_knight_on_c6(games_data):
    board, move = _board_after_user_move_for_result(games_data, USER, "loss", 6)
    assert move.uci() == "e5e4"
    assert _is_attacked_by(board, chess.C6, chess.WHITE, chess.D5)


def test_canonical_practice_queue_contains_two_missed_hanging_pieces(  # noqa: PLR0915
    pipeline_db_path: Path,
) -> None:
    conn = get_connection(pipeline_db_path)
    start_date = datetime(2026, 2, 1, tzinfo=UTC)
    end_date = datetime(2026, 2, 1, 23, 59, 59, tzinfo=UTC)
    try:
        recent_games = fetch_recent_games(
            conn,
            source="chesscom",
            time_control="bullet",
            start_date=start_date,
            end_date=end_date,
        )
        assert len(recent_games) == 2
        losses = [row for row in recent_games if row.get("result") == "loss"]
        assert len(losses) == 1
        loss_game_id = losses[0].get("game_id")
        assert loss_game_id

        practice_queue = tactic_repository(conn).fetch_practice_queue(
            source="chesscom",
            include_failed_attempt=False,
            limit=10,
        )
        loss_items = [
            row
            for row in practice_queue
            if row.get("game_id") == loss_game_id
            and row.get("motif") == "hanging_piece"
            and row.get("result") == "missed"
        ]
        assert len(loss_items) >= 2
        assert len({row.get("position_id") for row in loss_items}) >= 2

        tactic_rows = conn.execute(
            """
            SELECT t.target_piece
            FROM tactics t
            JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
            JOIN positions p ON p.position_id = t.position_id
            WHERE t.game_id = ?
            AND t.motif = 'hanging_piece'
            AND o.result = 'missed'
            AND COALESCE(p.user_to_move, TRUE) = FALSE
            """,
            [loss_game_id],
        ).fetchall()
        labels = {row[0] for row in tactic_rows if row[0] in {"knight", "bishop"}}
        assert {"knight", "bishop"}.issubset(labels)
    finally:
        conn.close()


def test_missed_hanging_piece_positions_are_post_blunder_positions(  # noqa: PLR0915
    pipeline_db_path: Path,
) -> None:
    conn = get_connection(pipeline_db_path)
    start_date = datetime(2026, 2, 1, tzinfo=UTC)
    end_date = datetime(2026, 2, 1, 23, 59, 59, tzinfo=UTC)
    try:
        recent_games = fetch_recent_games(
            conn,
            source="chesscom",
            time_control="bullet",
            start_date=start_date,
            end_date=end_date,
        )
        losses = [row for row in recent_games if row.get("result") == "loss"]
        assert len(losses) == 1
        loss_game_id = losses[0].get("game_id")
        assert loss_game_id

        tactic_rows = conn.execute(
            """
            SELECT t.tactic_id, t.position_id, t.best_uci, p.fen, t.target_piece, p.user_to_move
            FROM tactics t
            JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
            JOIN positions p ON p.position_id = t.position_id
            WHERE t.game_id = ?
            AND t.motif = 'hanging_piece'
            AND o.result = 'missed'
            AND COALESCE(p.user_to_move, TRUE) = FALSE
            """,
            [loss_game_id],
        ).fetchall()

        canonical: dict[str, tuple[object, object, object, object]] = {}
        for tactic_id, position_id, best_uci, fen, target_piece, _user_to_move in tactic_rows:
            if target_piece in {"knight", "bishop"} and target_piece not in canonical:
                canonical[str(target_piece)] = (tactic_id, position_id, best_uci, fen)

        assert set(canonical.keys()) == {"knight", "bishop"}

        queue_rows = conn.execute(
            """
            SELECT opportunity_id, position_id, fen, result
            FROM practice_queue
            WHERE game_id = ?
            """,
            [loss_game_id],
        ).fetchall()
        queue_by_id = {row[0]: row for row in queue_rows}

        for tactic_id, position_id, best_uci, fen in canonical.values():
            queue_row = queue_by_id.get(tactic_id)
            assert queue_row is not None
            assert queue_row[1] == position_id
            assert queue_row[2] == fen
            assert queue_row[3] == "missed"
            opportunity_id = queue_row[0]

            assert opportunity_id is not None
            assert position_id is not None
            assert best_uci
            assert fen

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
            assert position_row[1] is False
    finally:
        conn.close()
