import chess

from tactix.detect_tactics__motifs import BaseTacticDetector
from tactix.utils.logger import funclogger


@funclogger
def _is_new_hanging_piece(
    board_before: chess.Board,
    board_after: chess.Board,
    mover_color: bool,
) -> bool:
    if BaseTacticDetector.has_hanging_piece(board_before, mover_color):
        return False
    return BaseTacticDetector.has_hanging_piece(board_after, mover_color)
