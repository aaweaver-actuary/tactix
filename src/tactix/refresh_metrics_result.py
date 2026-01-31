from pydantic import BaseModel


class RefreshMetricsResult(BaseModel):
    source: str
    user: str
    metrics_version: int
    metrics_rows: int
