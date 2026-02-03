from tactix.config import Settings
from tactix.utils.logger import funclogger


@funclogger
def _resolve_chesscom_profile_value(settings: Settings) -> str:
    profile_value = settings.chesscom_profile or settings.chesscom.time_class
    if profile_value == "daily":
        return "correspondence"
    return profile_value
