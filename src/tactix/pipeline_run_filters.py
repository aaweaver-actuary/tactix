"""Pipeline run query filters."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class PipelineRunFilters(BaseModel):
    """Filters accepted by the pipeline run endpoint."""

    source: str | None = None
    profile: str | None = None
    user_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    use_fixture: bool = False
    fixture_name: str | None = None
    db_name: str | None = None
    reset_db: bool = False
