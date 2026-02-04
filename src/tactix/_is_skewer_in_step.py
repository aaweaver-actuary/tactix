import chess

from tactix._is_line_tactic import _is_line_tactic
from tactix.BaseTacticDetector import BaseTacticDetector
from tactix.line_tactic_helpers import LineTacticInputs, build_line_tactic_context
from tactix.utils.logger import funclogger


@funclogger
def _is_skewer_in_step(
    detector: BaseTacticDetector,
    board: chess.Board,
    start: chess.Square,
    step: int,
    opponent: bool,
) -> bool:
    return _is_line_tactic(
        build_line_tactic_context(LineTacticInputs(detector, board, start, step, opponent, True))
    )
