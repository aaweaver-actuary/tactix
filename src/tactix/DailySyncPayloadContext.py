"""Context for daily sync payload building."""

# pylint: disable=invalid-name

from dataclasses import dataclass

from tactix.config import Settings
from tactix.pipeline_state__pipeline import FetchContext, GameRow


@dataclass(frozen=True)
class DailySyncPayloadContext:  # pylint: disable=too-many-instance-attributes
    """Carries data required to build daily sync payloads."""

    settings: Settings
    fetch_context: FetchContext
    games: list[GameRow]
    raw_pgns_inserted: int
    raw_pgns_hashed: int
    raw_pgns_matched: int
    postgres_raw_pgns_inserted: int
    positions_count: int
    tactics_count: int
    metrics_version: int
    checkpoint_value: int | None
    last_timestamp_value: int
    backfill_mode: bool
