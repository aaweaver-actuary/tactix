from tactix.analyze_tactics__positions import _MATE_IN_ONE_UNCLEAR_SCORE_THRESHOLD, MATE_IN_ONE
from tactix.outcome_context import BaseOutcomeContext


def _should_mark_unclear_mate_in_one(
    context: BaseOutcomeContext,
    mate_in: int | None,
) -> bool:
    after_cp = context.after_cp
    if after_cp is None:
        return False
    return all(
        (
            mate_in == MATE_IN_ONE,
            context.best_move is not None,
            context.user_move_uci != context.best_move,
            context.result in {"missed", "failed_attempt"},
            after_cp >= _MATE_IN_ONE_UNCLEAR_SCORE_THRESHOLD,
        )
    )
