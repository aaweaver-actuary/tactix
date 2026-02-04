"""Context for daily sync completion events."""

from dataclasses import dataclass

from tactix.config import Settings
from tactix.pipeline_state__pipeline import GameRow


@dataclass(frozen=True)
class DailySyncCompleteContext:
    """Carries data for daily sync completion."""

    settings: Settings
    profile: str | None
    games: list[GameRow]
    raw_pgns_inserted: int
    postgres_raw_pgns_inserted: int
    positions_count: int
    tactics_count: int
    postgres_written: int
    postgres_synced: int
    metrics_version: int
    backfill_mode: bool
