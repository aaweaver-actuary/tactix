from datetime import date

from pydantic import BaseModel


class TacticsSearchFilters(BaseModel):
    source: str | None = None
    motif: str | None = None
    rating_bucket: str | None = None
    time_control: str | None = None
    start_date: date | None = None
    end_date: date | None = None
