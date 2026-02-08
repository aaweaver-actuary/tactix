from tactix._reclassify_motif import _reclassify_motif
from tactix._should_reclassify import _should_reclassify
from tactix.utils.logger import funclogger


@funclogger
def _reclassify_failed_attempt(result: str, delta: int, motif: str, user_motif: str) -> str:
    reclassify_motif = _reclassify_motif(motif, user_motif)
    if not _should_reclassify(result, delta, reclassify_motif):
        return result
    return "failed_attempt"
