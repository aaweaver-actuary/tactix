import chess

from tactix._score_best_line__after_move import _score_best_line__after_move
from tactix.StockfishEngine import StockfishEngine
from tactix.utils.logger import funclogger


@funclogger
def _compare_move__best_line(
    board: chess.Board,
    best_move: chess.Move | None,
    user_move_uci: str,
    after_cp: int,
    engine: StockfishEngine,
    mover_color: bool,
) -> int | None:
    if best_move is None or user_move_uci == best_move.uci():
        return None
    best_after_cp = _score_best_line__after_move(board, best_move, engine, mover_color)
    if best_after_cp is None:
        return None
    return after_cp - best_after_cp
