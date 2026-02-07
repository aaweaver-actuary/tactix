import logging
import shutil
from io import StringIO
from pathlib import Path

import chess
import chess.pgn

from tactix.config import Settings
from tactix.analyze_tactics__positions import MOTIF_DETECTORS
from tactix._infer_hanging_or_detected_motif import _infer_hanging_or_detected_motif
from tactix.analyze_position import analyze_position
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.StockfishEngine import StockfishEngine
from tactix.utils.logger import set_level


def first_move_position(path: Path) -> tuple[chess.Board | None, chess.Move | None]:
    text = path.read_text()
    for chunk in text.split("\n\n\n"):
        game = chess.pgn.read_game(StringIO(chunk))
        if not game:
            continue
        fen = game.headers.get("FEN")
        board = chess.Board(fen) if fen else game.board()
        moves = list(game.mainline_moves())
        if not moves:
            continue
        return board, moves[0]
    return None, None


def inspect(name: str, fixture: Path) -> None:
    board, move = first_move_position(fixture)
    if board is None or move is None:
        print(name, "not found")
        return
    motif = MOTIF_DETECTORS.infer_motif(board, move)
    inferred = _infer_hanging_or_detected_motif(board, move, board.turn)
    capture = board.is_capture(move)
    board_after = board.copy()
    board_after.push(move)
    hanging_capture = BaseTacticDetector.is_hanging_capture(board, board_after, move, board.turn)
    print(
        name,
        "motif",
        motif,
        "inferred",
        inferred,
        "capture",
        capture,
        "hanging",
        hanging_capture,
        "mate",
        board_after.is_checkmate(),
    )
    settings = Settings(
        stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
        stockfish_movetime_ms=60,
        stockfish_depth=12,
        stockfish_multipv=1,
    )
    with StockfishEngine(settings) as engine:
        result = analyze_position({"fen": board.fen(), "uci": move.uci()}, engine, settings)
    if result is None:
        print(name, "analyze_position", "none")
        return
    tactic_row, outcome_row = result
    print(
        name,
        "analyze_position",
        tactic_row.get("motif"),
        "best_uci",
        tactic_row.get("best_uci"),
        "result",
        outcome_row.get("result"),
    )


if __name__ == "__main__":
    set_level(logging.WARNING)
    base = Path("/Users/andy/tactix/tests/fixtures")
    inspect("hangingpiece", base / "hangingpiece.pgn")
    inspect("skewer", base / "skewer.pgn")
    inspect("discoveredattack", base / "discoveredattack.pgn")
