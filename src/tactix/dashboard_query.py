"""Dashboard query models and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast


@dataclass(frozen=True)
class DashboardQuery:
    """Filters used to query dashboard metrics and payloads."""

    source: str | None = None
    motif: str | None = None
    rating_bucket: str | None = None
    time_control: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


def resolve_dashboard_query(
    query: DashboardQuery | str | None = None,
    *,
    filters: DashboardQuery | None = None,
    **legacy: Any,
) -> DashboardQuery:
    """Resolve legacy inputs into a DashboardQuery instance."""
    if isinstance(query, DashboardQuery):
        return query
    if filters is None:
        filters = DashboardQuery(
            source=legacy.pop("source", None),
            motif=legacy.pop("motif", None),
            rating_bucket=legacy.pop("rating_bucket", None),
            time_control=legacy.pop("time_control", None),
            start_date=legacy.pop("start_date", None),
            end_date=legacy.pop("end_date", None),
        )
    if legacy:
        raise TypeError(f"Unexpected keyword arguments: {', '.join(sorted(legacy))}")
    if query is None:
        return filters
    return DashboardQuery(
        source=query,
        motif=filters.source,
        rating_bucket=filters.motif,
        time_control=filters.rating_bucket,
        start_date=cast(datetime | None, filters.time_control),
        end_date=filters.start_date,
    )


def clone_dashboard_query(
    query: DashboardQuery,
    **overrides: Any,
) -> DashboardQuery:
    """Clone a dashboard query with optional overrides."""
    return DashboardQuery(
        source=cast(str | None, overrides.get("source", query.source)),
        motif=cast(str | None, overrides.get("motif", query.motif)),
        rating_bucket=cast(str | None, overrides.get("rating_bucket", query.rating_bucket)),
        time_control=cast(str | None, overrides.get("time_control", query.time_control)),
        start_date=cast(datetime | None, overrides.get("start_date", query.start_date)),
        end_date=cast(datetime | None, overrides.get("end_date", query.end_date)),
    )
