from datetime import date
from typing import Annotated

from fastapi import Query


class DashboardQueryFilters:
    def __init__(
        self,
        source: Annotated[str | None, Query()] = None,
        rating_bucket: Annotated[str | None, Query()] = None,
        time_control: Annotated[str | None, Query()] = None,
        start_date: Annotated[date | None, Query()] = None,
        end_date: Annotated[date | None, Query()] = None,
    ) -> None:
        self.source = source
        self.rating_bucket = rating_bucket
        self.time_control = time_control
        self.start_date = start_date
        self.end_date = end_date
