import logging
from io import StringIO
from pathlib import Path
import shutil

import chess
import chess.pgn

from tactix.analyze_position import analyze_position
from tactix.config import Settings
from tactix.StockfishEngine import StockfishEngine

logging.disable(logging.CRITICAL)


def first_move_from_label(fixture_path: Path, label: str) -> tuple[chess.Board, chess.Move]:
    text = fixture_path.read_text()
    chunk = next(c for c in text.split("\n\n\n") if label in c)
    game = chess.pgn.read_game(StringIO(chunk))
    fen = game.headers.get("FEN")
    board = chess.Board(fen) if fen else game.board()
    move = list(game.mainline_moves())[0]
    return board, move


def first_move_from_fixture(fixture_path: Path) -> tuple[chess.Board, chess.Move]:
    text = fixture_path.read_text().strip()
    chunk = text.split("\n\n\n")[0]
    game = chess.pgn.read_game(StringIO(chunk))
    fen = game.headers.get("FEN")
    board = chess.Board(fen) if fen else game.board()
    move = list(game.mainline_moves())[0]
    return board, move


def analyze(board: chess.Board, move: chess.Move, settings: Settings) -> tuple[str, int | None]:
    with StockfishEngine(settings) as engine:
        tactic_row, _ = analyze_position(
            {
                "game_id": "debug",
                "position_id": 1,
                "fen": board.fen(),
                "uci": move.uci(),
            },
            engine,
            settings=settings,
        )
    return str(tactic_row["motif"]), tactic_row.get("mate_in")


mate_fixture = Path("/Users/andy/tactix/tests/fixtures/matein2.pgn")
mate_board, mate_move = first_move_from_fixture(mate_fixture)
mate_settings = Settings(
    stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
    stockfish_movetime_ms=60,
    stockfish_depth=12,
    stockfish_multipv=1,
)
print("matein2", analyze(mate_board, mate_move, mate_settings))

corr_fixture = Path("/Users/andy/tactix/tests/fixtures/chesscom_correspondence_sample.pgn")
cor_board, cor_move = first_move_from_label(
    corr_fixture,
    "Correspondence Fixture 12 - Hanging Piece High",
)
cor_settings = Settings(
    source="chesscom",
    chesscom_user="chesscom",
    chesscom_profile="correspondence",
    stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
    stockfish_movetime_ms=200,
    stockfish_depth=None,
    stockfish_multipv=1,
)
cor_settings.apply_chesscom_profile("correspondence")
print("correspondence_hanging", analyze(cor_board, cor_move, cor_settings))
