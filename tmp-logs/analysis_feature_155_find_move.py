import shutil
from pathlib import Path

import chess

from tactix.config import DEFAULT_BULLET_STOCKFISH_DEPTH, Settings
from tactix.StockfishEngine import StockfishEngine
from tactix.tactics_analyzer import analyze_position

FEN = "r6r/1b3pk1/p2p2p1/1p1Pp2p/4PP1q/2Pn2NP/BP3QPN/5RK1 w - - 3 35"

settings = Settings(
    source="chesscom",
    chesscom_user="chesscom",
    chesscom_profile="bullet",
    stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
    stockfish_movetime_ms=60,
    stockfish_depth=None,
    stockfish_multipv=1,
)
settings.apply_chesscom_profile("bullet")
print("depth", settings.stockfish_depth, "default", DEFAULT_BULLET_STOCKFISH_DEPTH)

board = chess.Board(FEN)

with StockfishEngine(settings) as engine:
    base = engine.analyse(board)
    best_move = base.best_move
    print(
        "best",
        best_move.uci() if best_move else None,
        "score",
        base.score_cp,
        "mate_in",
        base.mate_in,
    )
    candidates: list[tuple[str, int, float, str]] = []
    for move in board.legal_moves:
        position = {
            "game_id": "tmp",
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
        if result is None:
            continue
        tactic_row, outcome_row = result
        if tactic_row["motif"] == "discovered_attack":
            candidates.append(
                (
                    move.uci(),
                    outcome_row["eval_delta"],
                    float(tactic_row["severity"]),
                    tactic_row["best_uci"],
                )
            )
    candidates.sort(key=lambda row: row[1])
    print("top candidates", candidates[:10])

import chess

from tactix.config import DEFAULT_BULLET_STOCKFISH_DEPTH, Settings
