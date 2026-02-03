from tactix._fork_floor_for_settings import _fork_floor_for_settings
from tactix.config import Settings
from tactix.utils.logger import funclogger


@funclogger
def _apply_fork_severity_floor(
    severity: float,
    motif: str,
    settings: Settings | None,
) -> float:
    if motif != "fork":
        return severity
    floor = _fork_floor_for_settings(settings)
    if floor is None:
        return severity
    return max(severity, floor)
