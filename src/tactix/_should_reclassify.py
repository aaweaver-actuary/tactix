from tactix.analyze_tactics__positions import _FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS
from tactix.utils.logger import funclogger


@funclogger
def _should_reclassify(result: str, delta: int, reclassify_motif: str | None) -> bool:
    if result != "missed" or reclassify_motif is None:
        return False
    return delta > _FAILED_ATTEMPT_RECLASSIFY_THRESHOLDS[reclassify_motif]
