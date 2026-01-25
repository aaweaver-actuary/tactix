from pydantic import BaseModel, Field


class PracticeAttemptRequest(BaseModel):
    tactic_id: int
    position_id: int
    attempted_uci: str
    source: str | None = None
