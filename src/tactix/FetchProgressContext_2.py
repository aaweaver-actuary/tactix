"""Context for reporting fetch progress (duplicate)."""

from dataclasses import dataclass

from tactix.config import Settings
from tactix.pipeline_state__pipeline import FetchContext, ProgressCallback


@dataclass(frozen=True)
class FetchProgressContext:
    """Carries data for fetch progress notifications."""

    settings: Settings
    progress: ProgressCallback | None
    fetch_context: FetchContext
    backfill_mode: bool
    window_start_ms: int | None
    window_end_ms: int | None
    fetched_games: int
