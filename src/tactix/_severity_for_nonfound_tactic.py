from tactix.utils.logger import funclogger


@funclogger
def _severity_for_nonfound_tactic(base_cp: int, delta: int, motif: str) -> float:
    if motif == "discovered_check":
        return abs(delta) / 100.0
    return max(abs(base_cp), abs(delta)) / 100.0
