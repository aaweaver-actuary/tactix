from __future__ import annotations

from pathlib import Path

import chess

import sys
sys.path.append("/Users/andy/tactix")

from tactix.config import Settings
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position

fen = "3q2k1/5N2/8/8/8/8/8/3Q2K1 b - - 0 1"

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
    "uci": "d8d6",
    "san": "Qd6",
    "clock_seconds": None,
    "is_legal": True,
}

with StockfishEngine(settings) as engine:
    result = analyze_position(position, engine, settings=settings)
    print("result", result)
    board = chess.Board(fen)
    best_move = engine.analyse(board).best_move
    print("best_move", best_move)
    if best_move:
        captured = board.piece_at(best_move.to_square)
        print("captured", captured)
