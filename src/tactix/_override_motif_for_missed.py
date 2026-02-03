from tactix._should_override_motif import _should_override_motif
from tactix.utils.logger import funclogger


@funclogger
def _override_motif_for_missed(
    user_motif: str,
    best_motif: str | None,
    result: str,
) -> str:
    if not _should_override_motif(user_motif, best_motif, result):
        return user_motif
    return best_motif or user_motif
