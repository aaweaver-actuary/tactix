from datetime import datetime

from tactix.coerce_date_to_datetime__datetime import _coerce_date_to_datetime
from tactix.config import Settings, get_settings
from tactix.DashboardQueryFilters import DashboardQueryFilters
from tactix.normalize_source__source import _normalize_source


def _resolve_dashboard_filters(
    filters: DashboardQueryFilters,
) -> tuple[datetime | None, datetime | None, str | None, Settings]:
    start_datetime = _coerce_date_to_datetime(filters.start_date)
    end_datetime = _coerce_date_to_datetime(filters.end_date, end_of_day=True)
    normalized_source = _normalize_source(filters.source)
    settings = get_settings(source=normalized_source)
    return start_datetime, end_datetime, normalized_source, settings
