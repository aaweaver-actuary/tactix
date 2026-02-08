"""Dashboard query filter models."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class DashboardQueryFilters(BaseModel):
    """Filters accepted by the dashboard endpoints."""

    source: str | None = None
    rating_bucket: str | None = None
    time_control: str | None = None
    start_date: date | None = None
    end_date: date | None = None
