"""Context for no-games payload (duplicate)."""

# pylint: disable=invalid-name

from dataclasses import dataclass

from tactix.config import Settings
from tactix.pipeline_state__pipeline import FetchContext


@dataclass(frozen=True)
class NoGamesPayloadContext:
    """Carries data for no-games payloads."""

    settings: Settings
    conn: object
    backfill_mode: bool
    fetch_context: FetchContext
    last_timestamp_value: int
    window_filtered: int
