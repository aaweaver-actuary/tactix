from tactix._apply_outcome__unclear_variant import _apply_outcome__unclear_variant
from tactix._should_mark_unclear_fork import _should_mark_unclear_fork
from tactix.outcome_context import BaseOutcomeContext


def _apply_outcome__unclear_fork(
    context: BaseOutcomeContext | str,
    *args: object,
    **kwargs: object,
) -> str:
    return _apply_outcome__unclear_variant(
        _should_mark_unclear_fork,
        context,
        *args,
        **kwargs,
    )
