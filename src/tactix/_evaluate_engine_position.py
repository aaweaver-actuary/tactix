import chess

from tactix.analyze_tactics__positions import MATE_IN_TWO
from tactix.detect_tactics__motifs import BaseTacticDetector
from tactix.StockfishEngine import StockfishEngine
from tactix.utils.logger import funclogger


@funclogger
def _evaluate_engine_position(
    board: chess.Board,
    engine: StockfishEngine,
    mover_color: bool,
    motif_board: chess.Board,
) -> tuple[chess.Move | None, str | None, int, bool, bool]:
    engine_result = engine.analyse(board)
    best_move_obj = engine_result.best_move
    best_move = best_move_obj.uci() if best_move_obj else None
    base_cp = BaseTacticDetector.score_from_pov(engine_result.score_cp, mover_color, board.turn)
    mate_in_one = False
    mate_in_two = False
    if best_move_obj is not None:
        mate_board = motif_board.copy()
        mate_board.push(best_move_obj)
        mate_in_one = mate_board.is_checkmate()
    if engine_result.mate_in is not None and engine_result.mate_in == MATE_IN_TWO:
        mate_in_two = True
    return best_move_obj, best_move, base_cp, mate_in_one, mate_in_two
