from tactix._apply_mate_overrides import _apply_mate_overrides
from tactix._apply_outcome__failed_attempt_hanging_piece import (
    _apply_outcome__failed_attempt_hanging_piece,
)
from tactix._apply_outcome__failed_attempt_line_tactics import (
    _apply_outcome__failed_attempt_line_tactics,
)
from tactix._apply_outcome__unclear_discovered_attack import (
    _apply_outcome__unclear_discovered_attack,
)
from tactix._apply_outcome__unclear_discovered_check import _apply_outcome__unclear_discovered_check
from tactix._apply_outcome__unclear_fork import _apply_outcome__unclear_fork
from tactix._apply_outcome__unclear_hanging_piece import _apply_outcome__unclear_hanging_piece
from tactix._apply_outcome__unclear_pin import _apply_outcome__unclear_pin
from tactix._apply_outcome__unclear_skewer import _apply_outcome__unclear_skewer
from tactix._compute_eval__discovered_attack_unclear_threshold import (
    _compute_eval__discovered_attack_unclear_threshold,
)
from tactix._compute_eval__discovered_check_unclear_threshold import (
    _compute_eval__discovered_check_unclear_threshold,
)
from tactix._compute_eval__failed_attempt_threshold import (
    _compute_eval__failed_attempt_threshold,
)
from tactix._compute_eval__fork_unclear_threshold import _compute_eval__fork_unclear_threshold
from tactix._compute_eval__hanging_piece_unclear_threshold import (
    _compute_eval__hanging_piece_unclear_threshold,
)
from tactix._compute_eval__pin_unclear_threshold import _compute_eval__pin_unclear_threshold
from tactix._compute_eval__skewer_unclear_threshold import _compute_eval__skewer_unclear_threshold
from tactix.config import Settings


def _apply_outcome_overrides(
    result: str,
    motif: str,
    best_motif: str | None,
    best_move: str | None,
    user_move_uci: str,
    swing: int | None,
    after_cp: int,
    mate_in_one: bool,
    mate_in_two: bool,
    settings: Settings | None,
) -> tuple[str, str, int | None]:
    result, motif = _apply_outcome__failed_attempt_line_tactics(
        result, motif, best_motif, swing, settings
    )
    result, motif = _apply_outcome__failed_attempt_hanging_piece(
        result,
        motif,
        best_motif,
        swing,
        _compute_eval__failed_attempt_threshold("hanging_piece", settings),
    )
    result = _apply_outcome__unclear_fork(
        result,
        motif,
        best_move,
        user_move_uci,
        swing,
        _compute_eval__fork_unclear_threshold(settings),
    )
    result = _apply_outcome__unclear_skewer(
        result,
        motif,
        best_move,
        user_move_uci,
        swing,
        _compute_eval__skewer_unclear_threshold(settings),
    )
    result = _apply_outcome__unclear_discovered_attack(
        result,
        motif,
        best_move,
        user_move_uci,
        swing,
        _compute_eval__discovered_attack_unclear_threshold(settings),
    )
    result = _apply_outcome__unclear_discovered_check(
        result,
        motif,
        best_move,
        user_move_uci,
        swing,
        _compute_eval__discovered_check_unclear_threshold(settings),
    )
    result = _apply_outcome__unclear_hanging_piece(
        result,
        motif,
        best_move,
        user_move_uci,
        swing,
        _compute_eval__hanging_piece_unclear_threshold(settings),
    )
    result = _apply_outcome__unclear_pin(
        result,
        motif,
        best_move,
        user_move_uci,
        swing,
        _compute_eval__pin_unclear_threshold(settings),
    )
    return _apply_mate_overrides(
        result,
        motif,
        best_move,
        user_move_uci,
        swing,
        after_cp,
        mate_in_one,
        mate_in_two,
    )
