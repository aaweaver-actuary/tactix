"""Compute severity for a tactic outcome."""

from tactix._severity_for_found_tactic import _severity_for_found_tactic
from tactix._severity_for_nonfound_tactic import _severity_for_nonfound_tactic
from tactix.utils.logger import funclogger


@funclogger
def _severity_for_result(
    base_cp: int,
    delta: int,
    motif: str,
    mate_in: int | None,
    result: str,
) -> float:
    if result == "found":
        return _severity_for_found_tactic(base_cp, delta, motif, mate_in)
    return _severity_for_nonfound_tactic(base_cp, delta, motif)
