from tactix._is_swing_at_least import _is_swing_at_least
from tactix.analyze_tactics__positions import _MATE_IN_TWO_UNCLEAR_SWING_THRESHOLD, MATE_IN_TWO
from tactix.outcome_context import BaseOutcomeContext


def _should_mark_unclear_mate_in_two(
    context: BaseOutcomeContext,
    mate_in: int | None,
) -> bool:
    return all(
        (
            mate_in == MATE_IN_TWO,
            context.best_move is not None,
            context.user_move_uci != context.best_move,
            context.result == "unclear",
            _is_swing_at_least(context.swing, _MATE_IN_TWO_UNCLEAR_SWING_THRESHOLD),
        )
    )
