from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import chess

PROJECT_ROOT = Path("/Users/andy/tactix")
sys.path.append(str(PROJECT_ROOT))

from tactix.config import Settings
from tactix.stockfish_runner import StockfishEngine
from tests.fixture_helpers import find_missed_position
from tactix.tactics_analyzer import analyze_position


@dataclass
class Candidate:
    name: str
    fen: str


CANDIDATES = [
    Candidate("bishop_attacks_queen", "3q2k1/4B3/8/8/8/8/8/6K1 b - - 0 1"),
    Candidate("bishop_attacks_queen_with_queen", "3q2k1/4B3/8/7Q/8/8/8/6K1 b - - 0 1"),
    Candidate("bishop_attacks_queen_with_rook", "3q2k1/4B3/8/8/8/8/8/5RK1 b - - 0 1"),
    Candidate("bishop_attacks_queen_king_h7", "3q4/4B2k/8/7Q/8/8/8/6K1 b - - 0 1"),
    Candidate("bishop_attacks_queen_king_h7_queen_g6", "3q4/4B2k/6Q1/8/8/8/8/6K1 b - - 0 1"),
    Candidate("bishop_attacks_queen_king_h7_queen_h5", "3q4/4B2k/8/7Q/8/8/8/6K1 b - - 0 1"),
    Candidate("bishop_attacks_queen_king_h7_queen_f6", "3q4/4B2k/5Q2/8/8/8/8/6K1 b - - 0 1"),
    Candidate("knight_attacks_queen", "3q2k1/8/8/8/8/8/5N2/6K1 b - - 0 1"),
    Candidate("knight_attacks_queen_with_queen", "3q2k1/8/8/7Q/8/8/5N2/6K1 b - - 0 1"),
    Candidate("knight_attacks_queen_with_rook", "3q2k1/8/8/8/8/8/5N2/5RK1 b - - 0 1"),
    Candidate("knight_with_queen_on_h5", "3q2k1/5N2/8/7Q/8/8/8/6K1 b - - 0 1"),
    Candidate("knight_with_queen_and_rook", "3q2k1/5N2/8/7Q/8/8/8/5RK1 b - - 0 1"),
    Candidate("knight_with_queen_on_g4", "3q2k1/5N2/8/8/6Q1/8/8/6K1 b - - 0 1"),
    Candidate("knight_with_queen_on_g4_king_g7", "3q4/5N1k/8/8/6Q1/8/8/6K1 b - - 0 1"),
    Candidate("knight_with_queen_on_h5_king_g7", "3q4/5N1k/8/7Q/8/8/8/6K1 b - - 0 1"),
    Candidate("knight_with_queen_on_f6_king_g7", "3q4/5N1k/5Q2/8/8/8/8/6K1 b - - 0 1"),
]


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


for candidate in CANDIDATES:
    position = {
        "game_id": candidate.name,
        "user": "chesscom",
        "source": "chesscom",
        "fen": candidate.fen,
        "ply": 0,
        "move_number": 1,
        "side_to_move": "black",
        "uci": "0000",
        "san": "",
        "clock_seconds": None,
        "is_legal": True,
    }
    print("\n===", candidate.name, "===")
    print(candidate.fen)
    try:
        with StockfishEngine(settings) as engine:
            missed_position, result = find_missed_position(
                position, engine, settings, "hanging_piece"
            )
            tactic_row, outcome_row = result
            board = chess.Board(candidate.fen)
            best_move = chess.Move.from_uci(tactic_row["best_uci"])
            captured = board.piece_at(best_move.to_square)
            print("best", tactic_row["best_uci"], "captured", captured)
            print(
                "missed uci",
                missed_position["uci"],
                "delta",
                outcome_row["eval_delta"],
                "result",
                outcome_row["result"],
                "motif",
                tactic_row["motif"],
            )
            if candidate.name == "knight_with_queen_on_g4":
                all_missed = []
                for move in board.legal_moves:
                    if tactic_row["best_uci"] == move.uci():
                        continue
                    candidate_move = dict(position)
                    candidate_move["uci"] = move.uci()
                    candidate_move["san"] = board.san(move)
                    result = analyze_position(candidate_move, engine, settings=settings)
                    if not result:
                        continue
                    tactic_row2, outcome_row2 = result
                    if (
                        tactic_row2["motif"] == "hanging_piece"
                        and outcome_row2["result"] == "missed"
                    ):
                        all_missed.append((move.uci(), outcome_row2["eval_delta"]))
                print("all missed moves", all_missed)
    except Exception as exc:
        print("no missed hanging piece:", exc)
