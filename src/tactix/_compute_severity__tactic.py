from tactix._apply_fork_severity_floor import _apply_fork_severity_floor
from tactix._severity_for_result import _severity_for_result
from tactix.analyze_tactics__positions import _SEVERITY_MAX
from tactix.config import Settings
from tactix.utils.logger import funclogger


@funclogger
def _compute_severity__tactic(
    base_cp: int,
    delta: int,
    motif: str,
    mate_in: int | None,
    result: str,
    settings: Settings | None,
) -> float:
    severity = _severity_for_result(base_cp, delta, motif, mate_in, result)
    severity = min(severity, _SEVERITY_MAX)
    return _apply_fork_severity_floor(severity, motif, settings)
