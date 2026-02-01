from __future__ import annotations

import sys
from pathlib import Path

import chess

PROJECT_ROOT = Path("/Users/andy/tactix")
sys.path.append(str(PROJECT_ROOT))

from tactix.config import Settings
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position

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

base_board = chess.Board(None)
base_board.set_piece_at(chess.parse_square("g8"), chess.Piece(chess.KING, chess.BLACK))
base_board.set_piece_at(chess.parse_square("d8"), chess.Piece(chess.QUEEN, chess.BLACK))
base_board.set_piece_at(chess.parse_square("f7"), chess.Piece(chess.KNIGHT, chess.WHITE))
base_board.set_piece_at(chess.parse_square("g1"), chess.Piece(chess.KING, chess.WHITE))
base_board.turn = chess.BLACK

solutions = []

with StockfishEngine(settings) as engine:
    for square in chess.SQUARES:
        if square in [chess.parse_square("g8"), chess.parse_square("d8"), chess.parse_square("f7"), chess.parse_square("g1")]:
            continue
        board = base_board.copy()
        board.set_piece_at(square, chess.Piece(chess.QUEEN, chess.WHITE))
        fen = board.fen()
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
        for move in board.legal_moves:
            candidate = dict(position)
            candidate["uci"] = move.uci()
            candidate["san"] = board.san(move)
            result = analyze_position(candidate, engine, settings=settings)
            if not result:
                continue
            tactic_row, outcome_row = result
            if tactic_row["motif"] != "hanging_piece" or outcome_row["result"] != "missed":
                continue
            if move.from_square != chess.parse_square("g8"):
                solutions.append((chess.square_name(square), move.uci(), outcome_row["eval_delta"], fen))
                break

print("found", len(solutions), "solutions")
for entry in solutions[:10]:
    print(entry)
