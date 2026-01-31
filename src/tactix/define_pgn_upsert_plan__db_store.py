from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PgnUpsertPlan:
    pgn_text: str
    pgn_hash: str
    pgn_version: int
    normalized_pgn: str | None
    metadata: Mapping[str, object]
    fetched_at: datetime
    ingested_at: datetime
    last_timestamp_ms: int
    cursor: object | None
