"""Shared pipeline state types and constants."""

from __future__ import annotations

from collections.abc import Callable

from tactix.utils.logger import Logger

logger = Logger("tactix.pipeline")

ANALYSIS_PROGRESS_BUCKETS = 20
DEFAULT_SYNC_LIMIT = 50
INDEX_OFFSET = 1
RESUME_INDEX_START = 0
SINGLE_PGN_CHUNK = 1
ZERO_COUNT = 0
LICHESS_BLACK_PROFILES = {"bullet", "blitz", "rapid", "classical", "correspondence"}
CHESSCOM_BLACK_PROFILES = {
    "bullet",
    "blitz",
    "rapid",
    "classical",
    "correspondence",
    "daily",
}


ProgressCallback = Callable[[dict[str, object]], None]
