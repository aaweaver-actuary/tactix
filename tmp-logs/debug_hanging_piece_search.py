import shutil
from pathlib import Path

import chess

from tactix.config import Settings
from tactix.stockfish_runner import StockfishEngine
from tactix.tactics_analyzer import analyze_position


def find_missed_hanging_moves(fen: str) -> list[tuple[str, str, str]]:
    board = chess.Board(fen)
    settings = Settings(
        source="chesscom",
        chesscom_user="chesscom",
        chesscom_profile="bullet",
        stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
    )
    settings.apply_chesscom_profile("bullet")
    settings.stockfish_movetime_ms = 60
    settings.stockfish_depth = 8
    settings.stockfish_multipv = 2
    settings.stockfish_random_seed = 1

    candidates: list[tuple[str, str, str]] = []
    with StockfishEngine(settings) as engine:
        for move in board.legal_moves:
            position = {
                "game_id": "loss-game",
                "user": "chesscom",
                "source": "chesscom",
                "fen": board.fen(),
                "ply": board.ply(),
                "move_number": board.fullmove_number,
                "side_to_move": "white" if board.turn == chess.WHITE else "black",
                "uci": move.uci(),
                "san": board.san(move),
                "clock_seconds": None,
                "is_legal": True,
            }
            result = analyze_position(position, engine, settings=settings)
            if not result:
                continue
            tactic_row, outcome_row = result
            if tactic_row["motif"] != "hanging_piece":
                continue
            best_uci = tactic_row.get("best_uci") or ""
            if not best_uci:
                continue
            best_move = chess.Move.from_uci(best_uci)
            if not board.is_capture(best_move):
                continue
            captured = board.piece_at(best_move.to_square)
            if not captured:
                continue
            mover = board.piece_at(move.from_square)
            mover_symbol = mover.symbol() if mover else "?"
            candidates.append(
                (
                    move.uci(),
                    best_uci,
                    captured.symbol(),
                    mover_symbol,
                    outcome_row["result"],
                    outcome_row.get("eval_delta"),
                )
            )
    return candidates


if __name__ == "__main__":
    import os

    FEN = os.getenv("TACTIX_DEBUG_FEN", "3q2k1/5ppp/8/4pn2/2BbP3/2P2N2/5PPP/3Q2K1 w - - 0 1")
    matches = find_missed_hanging_moves(FEN)
    print(f"FEN: {FEN}")
    if not matches:
        print("No hanging piece candidates found.")
    else:
        for move, best, captured, mover, result, delta in matches:
            print(
                "candidate",
                move,
                "best",
                best,
                "captures",
                captured,
                "mover",
                mover,
                "result",
                result,
                "delta",
                delta,
            )
