"""Define the PGN upsert plan for persistence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class PgnUpsertPlan:  # pylint: disable=too-many-instance-attributes
    """Payload for inserting or updating PGN rows."""

    pgn_text: str
    pgn_hash: str
    pgn_version: int
    normalized_pgn: str | None
    metadata: Mapping[str, object]
    fetched_at: datetime
    ingested_at: datetime
    last_timestamp_ms: int
    cursor: object | None
