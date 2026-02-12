"""Evaluate a position using the engine and derive metadata."""

import chess

from tactix.analyze_tactics__positions import MATE_IN_TWO
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.StockfishEngine import StockfishEngine
from tactix.utils.logger import funclogger


@funclogger
def _evaluate_engine_position(
    board: chess.Board,
    engine: StockfishEngine,
    mover_color: bool,
    motif_board: chess.Board,
) -> tuple[chess.Move | None, str | None, int, bool, bool, str | None, int]:
    """Return engine analysis results and mate flags for a position."""
    engine_result = engine.analyse(board)
    best_move_obj = engine_result.best_move
    best_move = best_move_obj.uci() if best_move_obj else None
    best_line_uci = engine_result.best_line_uci or best_move
    base_cp = BaseTacticDetector.score_from_pov(engine_result.score_cp, mover_color, board.turn)
    mate_in_one = _detect_mate_in_one(best_move_obj, motif_board)
    mate_in_two = _detect_mate_in_two(engine_result.mate_in)
    return (
        best_move_obj,
        best_move,
        base_cp,
        mate_in_one,
        mate_in_two,
        best_line_uci,
        engine_result.depth,
    )


def _detect_mate_in_one(best_move: chess.Move | None, board: chess.Board) -> bool:
    """Return True when the best move is an immediate checkmate."""
    if best_move is None:
        return False
    mate_board = board.copy()
    mate_board.push(best_move)
    return mate_board.is_checkmate()


def _detect_mate_in_two(mate_in: int | None) -> bool:
    """Return True when the engine result reports mate in two."""
    return mate_in == MATE_IN_TWO
