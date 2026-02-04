"""Apply unclear outcome logic for hanging piece motifs."""

from tactix._apply_outcome__unclear_variant import _apply_outcome__unclear_variant
from tactix._should_mark_unclear_hanging_piece import _should_mark_unclear_hanging_piece
from tactix.outcome_context import BaseOutcomeContext


def _apply_outcome__unclear_hanging_piece(
    context: BaseOutcomeContext | str,
    *args: object,
    **kwargs: object,
) -> str:
    return _apply_outcome__unclear_variant(
        _should_mark_unclear_hanging_piece,
        context,
        *args,
        **kwargs,
    )
