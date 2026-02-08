import chess

from tactix.LineTacticContext import LineTacticContext
from tactix.PinDetector import PinDetector
from tactix.line_tactic_context_builder import (
    DEFAULT_LINE_TACTIC_CONTEXT_BUILDER,
    LineTacticContextInputs,
)


def test_line_tactic_context_builder_builds_context() -> None:
    board = chess.Board()
    detector = PinDetector()
    inputs = LineTacticContextInputs(
        detector=detector,
        board=board,
        start=chess.E2,
        step=1,
        opponent=False,
        target_stronger=True,
    )

    context = DEFAULT_LINE_TACTIC_CONTEXT_BUILDER.build(inputs)

    assert isinstance(context, LineTacticContext)
    assert context.detector is detector
    assert context.board is board
    assert context.start == chess.E2
    assert context.step == 1
    assert context.opponent is False
    assert context.target_stronger is True
