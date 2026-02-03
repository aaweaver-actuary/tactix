from tactix._apply_outcome__unclear_mate_in_one import _apply_outcome__unclear_mate_in_one
from tactix._apply_outcome__unclear_mate_in_two import (
    _apply_outcome__unclear_mate_in_two,
)
from tactix._override_mate_motif import _override_mate_motif
from tactix._resolve_mate_in import _resolve_mate_in
from tactix._should_upgrade_mate_result import _should_upgrade_mate_result


def _apply_mate_overrides(
    result: str,
    motif: str,
    best_move: str | None,
    user_move_uci: str,
    swing: int | None,
    after_cp: int,
    mate_in_one: bool,
    mate_in_two: bool,
) -> tuple[str, str, int | None]:
    mate_in = _resolve_mate_in(mate_in_one, mate_in_two)
    motif = _override_mate_motif(motif, mate_in)
    result = _apply_outcome__unclear_mate_in_one(
        result,
        best_move,
        user_move_uci,
        after_cp,
        mate_in,
    )
    result = _apply_outcome__unclear_mate_in_two(
        result,
        best_move,
        user_move_uci,
        swing,
        mate_in,
    )
    if _should_upgrade_mate_result(
        result,
        best_move,
        user_move_uci,
        after_cp,
        swing,
        mate_in,
    ):
        result = "failed_attempt"
    return result, motif, mate_in
