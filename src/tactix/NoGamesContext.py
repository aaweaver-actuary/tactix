"""Context for no-games handling."""

# pylint: disable=invalid-name

from dataclasses import dataclass

from tactix.config import Settings
from tactix.pipeline_state__pipeline import FetchContext, ProgressCallback


@dataclass(frozen=True)
class NoGamesContext:
    """Carries data for no-games handling."""

    settings: Settings
    conn: object
    progress: ProgressCallback | None
    backfill_mode: bool
    fetch_context: FetchContext
    last_timestamp_value: int
    window_filtered: int
