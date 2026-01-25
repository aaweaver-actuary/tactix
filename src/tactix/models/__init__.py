from pydantic import BaseModel, Field


class PracticeAttemptRequest(BaseModel):
    tactic_id: int
    position_id: int
    attempted_uci: str
    source: str | None = None
    served_at_ms: int | None = None
