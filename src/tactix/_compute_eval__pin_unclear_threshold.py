from tactix.analyze_tactics__positions import _PIN_UNCLEAR_SWING_THRESHOLD
from tactix.config import Settings
from tactix.utils.logger import funclogger


@funclogger
def _compute_eval__pin_unclear_threshold(settings: Settings | None) -> int | None:
    del settings
    return _PIN_UNCLEAR_SWING_THRESHOLD
