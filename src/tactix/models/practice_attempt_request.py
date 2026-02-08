"""Request model for practice attempt submissions."""

from pydantic import BaseModel


class PracticeAttemptRequest(BaseModel):
    """Payload describing a user's practice attempt."""

    tactic_id: int
    position_id: int
    attempted_uci: str
    source: str | None = None
    served_at_ms: int | None = None
