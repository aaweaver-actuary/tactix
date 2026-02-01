from __future__ import annotations

import sys
from pathlib import Path

import chess

sys.path.append("/Users/andy/tactix")

from tactix.config import Settings
from tactix.stockfish_runner import StockfishEngine
from tests.fixture_helpers import find_missed_position

fen = "3q4/4B2k/8/4N3/6Q1/8/8/6K1 b - - 0 1"

settings = Settings(
    source="chesscom",
    chesscom_user="chesscom",
    chesscom_profile="bullet",
    stockfish_path=Path("stockfish"),
    stockfish_movetime_ms=60,
    stockfish_depth=10,
    stockfish_multipv=1,
)
settings.apply_chesscom_profile("bullet")

position = {
    "game_id": "search",
    "user": "chesscom",
    "source": "chesscom",
    "fen": fen,
    "ply": 0,
    "move_number": 1,
    "side_to_move": "black",
    "uci": "0000",
    "san": "",
    "clock_seconds": None,
    "is_legal": True,
}

with StockfishEngine(settings) as engine:
    missed_position, result = find_missed_position(position, engine, settings, "hanging_piece")
    tactic_row, outcome_row = result
    board = chess.Board(fen)
    best_move = chess.Move.from_uci(tactic_row["best_uci"])
    print("best", tactic_row["best_uci"], "captured", board.piece_at(best_move.to_square))
    print("missed", missed_position["uci"], "delta", outcome_row["eval_delta"], "result", outcome_row["result"], "motif", tactic_row["motif"])
