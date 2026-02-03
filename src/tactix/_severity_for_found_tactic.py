from tactix.analyze_tactics__positions import _SEVERITY_MAX, MATE_IN_ONE, MATE_IN_TWO
from tactix.utils.logger import funclogger


@funclogger
def _severity_for_found_tactic(
    base_cp: int,
    delta: int,
    motif: str,
    mate_in: int | None,
) -> float:
    if mate_in in {MATE_IN_ONE, MATE_IN_TWO} or motif == "mate":
        return _SEVERITY_MAX
    if motif == "pin":
        return abs(base_cp) / 100.0
    return max(abs(delta) / 100.0, 0.01)
