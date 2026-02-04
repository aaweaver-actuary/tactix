"""Context for no-games-after-dedupe handling."""

# pylint: disable=invalid-name

from dataclasses import dataclass

from tactix.config import Settings
from tactix.pipeline_state__pipeline import FetchContext, GameRow, ProgressCallback


@dataclass(frozen=True)
class NoGamesAfterDedupeContext:  # pylint: disable=too-many-instance-attributes
    """Carries data for no-games-after-dedupe handling."""

    settings: Settings
    conn: object
    progress: ProgressCallback | None
    backfill_mode: bool
    fetch_context: FetchContext
    last_timestamp_value: int
    games: list[GameRow]
    window_filtered: int
