"""Apply unclear pin outcomes when appropriate."""

from tactix._apply_outcome__unclear_variant import _apply_outcome__unclear_variant
from tactix._should_mark_unclear_pin import _should_mark_unclear_pin
from tactix.outcome_context import BaseOutcomeContext


def _apply_outcome__unclear_pin(
    context: BaseOutcomeContext | str,
    *args: object,
    **kwargs: object,
) -> str:
    return _apply_outcome__unclear_variant(
        _should_mark_unclear_pin,
        context,
        *args,
        **kwargs,
    )
