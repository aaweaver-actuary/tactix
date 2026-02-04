"""Context for no-games-after-dedupe payload."""

# pylint: disable=invalid-name

from dataclasses import dataclass

from tactix.config import Settings
from tactix.pipeline_state__pipeline import FetchContext, GameRow


@dataclass(frozen=True)
class NoGamesAfterDedupePayloadContext:
    """Carries data for no-games-after-dedupe payloads."""

    settings: Settings
    conn: object
    backfill_mode: bool
    fetch_context: FetchContext
    last_timestamp_value: int
    games: list[GameRow]
    window_filtered: int
