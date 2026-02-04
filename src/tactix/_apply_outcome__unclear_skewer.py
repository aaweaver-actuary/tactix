"""Apply unclear skewer outcomes when needed."""

from tactix._apply_outcome__unclear_variant import _apply_outcome__unclear_variant

# pylint: disable=redefined-outer-name
from tactix._should_mark_unclear_skewer import _should_mark_unclear_skewer
from tactix.outcome_context import BaseOutcomeContext


def _apply_outcome__unclear_skewer(
    context: BaseOutcomeContext | str,
    *args: object,
    **kwargs: object,
) -> str:
    return _apply_outcome__unclear_variant(
        _should_mark_unclear_skewer,
        context,
        *args,
        **kwargs,
    )
