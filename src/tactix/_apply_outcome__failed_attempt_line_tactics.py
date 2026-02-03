from tactix._apply_outcome__failed_attempt_discovered_attack import (
    _apply_outcome__failed_attempt_discovered_attack,
)
from tactix._apply_outcome__failed_attempt_discovered_check import (
    _apply_outcome__failed_attempt_discovered_check,
)
from tactix._apply_outcome__failed_attempt_pin import _apply_outcome__failed_attempt_pin
from tactix._apply_outcome__failed_attempt_skewer import _apply_outcome__failed_attempt_skewer
from tactix._compute_eval__failed_attempt_threshold import (
    _compute_eval__failed_attempt_threshold,
)
from tactix.config import Settings


def _apply_outcome__failed_attempt_line_tactics(
    result: str,
    motif: str,
    best_motif: str | None,
    swing: int | None,
    settings: Settings | None,
) -> tuple[str, str]:
    result, motif = _apply_outcome__failed_attempt_pin(
        result,
        motif,
        best_motif,
        swing,
        _compute_eval__failed_attempt_threshold("pin", settings),
    )
    result, motif = _apply_outcome__failed_attempt_skewer(
        result,
        motif,
        best_motif,
        swing,
        _compute_eval__failed_attempt_threshold("skewer", settings),
    )
    result, motif = _apply_outcome__failed_attempt_discovered_attack(
        result,
        motif,
        best_motif,
        swing,
        _compute_eval__failed_attempt_threshold("discovered_attack", settings),
    )
    return _apply_outcome__failed_attempt_discovered_check(
        result,
        motif,
        best_motif,
        swing,
        _compute_eval__failed_attempt_threshold("discovered_check", settings),
    )
