import chess

from tactix._score_after_move import _score_after_move
from tactix.StockfishEngine import StockfishEngine
from tactix.utils.logger import funclogger


@funclogger
def _score_best_line__after_move(
    board: chess.Board,
    best_move: chess.Move | None,
    engine: StockfishEngine,
    mover_color: bool,
) -> int | None:
    if best_move is None:
        return None
    best_board = board.copy()
    best_board.push(best_move)
    return _score_after_move(best_board, engine, mover_color)
