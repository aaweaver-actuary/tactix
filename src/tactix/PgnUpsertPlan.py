from datetime import datetime

from pydantic import BaseModel


class PgnUpsertPlan(BaseModel):
    """Payload for inserting or updating PGN rows."""

    pgn_text: str
    pgn_hash: str
    pgn_version: int
    normalized_pgn: str | None
    metadata: dict[str, object]
    fetched_at: datetime
    ingested_at: datetime
    last_timestamp_ms: int
    cursor: object
