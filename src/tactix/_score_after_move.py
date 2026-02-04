"""Score positions after a move with the engine."""

import chess

from tactix.detect_tactics__motifs import BaseTacticDetector
from tactix.StockfishEngine import StockfishEngine
from tactix.utils.logger import funclogger


@funclogger
def _score_after_move(board: chess.Board, engine: StockfishEngine, mover_color: bool) -> int:
    return BaseTacticDetector.score_from_pov(
        engine.analyse(board).score_cp, mover_color, board.turn
    )
