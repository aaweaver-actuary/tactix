"""Pydantic model for refresh metrics responses."""

from pydantic import BaseModel


class RefreshMetricsResult(BaseModel):
    """Response payload for metrics refresh calls."""

    source: str
    user: str
    metrics_version: int
    metrics_rows: int
