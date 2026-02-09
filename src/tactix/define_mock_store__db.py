"""Mock database store implementation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import cast

from tactix.dashboard_query import DashboardQuery, resolve_dashboard_query
from tactix.define_base_db_store__db_store import BaseDbStore
from tactix.define_base_db_store_context__db_store import BaseDbStoreContext
from tactix.tactic_scope import is_allowed_motif_filter, is_scoped_motif_row


class MockDbStore(BaseDbStore):
    """Mock database store that serves in-memory dashboard payloads."""

    def __init__(
        self, context: BaseDbStoreContext, payload: dict[str, object] | None = None
    ) -> None:
        super().__init__(context)
        self._payload = payload or {
            "source": context.settings.source,
            "user": context.settings.user,
            "metrics": [],
            "recent_games": [],
            "positions": [],
            "tactics": [],
            "metrics_version": 0,
        }

    def get_dashboard_payload(
        self,
        query: DashboardQuery | str | None = None,
        *,
        filters: DashboardQuery | None = None,
        **legacy: object,
    ) -> dict[str, object]:
        query = resolve_dashboard_query(query, filters=filters, **legacy)
        payload = dict(self._payload)
        normalized_source = None if query.source in (None, "all") else query.source
        payload["source"] = normalized_source or "all"
        payload["user"] = self.settings.user
        payload["metrics"] = _filter_rows(
            cast(Iterable[object], payload.get("metrics", [])),
            DashboardQuery(
                source=normalized_source,
                motif=query.motif,
                rating_bucket=query.rating_bucket,
                time_control=query.time_control,
                start_date=query.start_date,
                end_date=query.end_date,
            ),
        )
        payload["recent_games"] = _filter_rows(
            cast(Iterable[object], payload.get("recent_games", [])),
            DashboardQuery(
                source=normalized_source,
                motif=query.motif,
                rating_bucket=query.rating_bucket,
                time_control=query.time_control,
                start_date=query.start_date,
                end_date=query.end_date,
            ),
        )
        payload["positions"] = _filter_rows(
            cast(Iterable[object], payload.get("positions", [])),
            DashboardQuery(
                source=normalized_source,
                motif=query.motif,
                rating_bucket=query.rating_bucket,
                time_control=query.time_control,
                start_date=query.start_date,
                end_date=query.end_date,
            ),
        )
        payload["tactics"] = _filter_rows(
            cast(Iterable[object], payload.get("tactics", [])),
            DashboardQuery(
                source=normalized_source,
                motif=query.motif,
                rating_bucket=query.rating_bucket,
                time_control=query.time_control,
                start_date=query.start_date,
                end_date=query.end_date,
            ),
        )
        return payload


def _filter_rows(
    rows: Iterable[object],
    query: DashboardQuery,
) -> list[object]:
    filtered: list[object] = []
    for row in rows:
        if not isinstance(row, dict):
            filtered.append(row)
            continue
        row_dict = cast(Mapping[str, object], row)
        if not _row_matches_filters(
            row_dict,
            query,
        ):
            continue
        filtered.append(row)
    return filtered


def _row_matches_filters(
    row: Mapping[str, object],
    query: DashboardQuery,
) -> bool:
    return all(
        (
            _matches_value(row, "source", query.source),
            _matches_scoped_motif(row, query.motif),
            _matches_value(row, "rating_bucket", query.rating_bucket),
            _matches_value(row, "time_control", query.time_control),
            _matches_date_range(row, query.start_date, query.end_date),
        )
    )


def _matches_scoped_motif(row: Mapping[str, object], motif: str | None) -> bool:
    mate_type = row.get("mate_type")
    if motif is None:
        return _matches_row_motif(row, mate_type)
    return _matches_requested_motif(row, motif, mate_type)


def _matches_row_motif(row: Mapping[str, object], mate_type: object | None) -> bool:
    row_motif = row.get("motif")
    if row_motif is None:
        return True
    return is_scoped_motif_row(str(row_motif), mate_type or None)


def _matches_requested_motif(
    row: Mapping[str, object],
    motif: str,
    mate_type: object | None,
) -> bool:
    if not is_allowed_motif_filter(motif) or not _matches_value(row, "motif", motif):
        return False
    return motif != "mate" or mate_type is not None


def _matches_value(row: Mapping[str, object], key: str, value: str | None) -> bool:
    if value is None:
        return True
    row_value = row.get(key)
    if row_value is None:
        return True
    return row_value == value


def _matches_date_range(
    row: Mapping[str, object],
    start_date: datetime | None,
    end_date: datetime | None,
) -> bool:
    if start_date is None and end_date is None:
        return True
    row_date = _extract_date(row)
    return _date_in_range(row_date, start_date, end_date)


def _date_in_range(
    row_date: date | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> bool:
    if row_date is None:
        return True
    start_value = _coerce_bound(start_date)
    end_value = _coerce_bound(end_date)
    return _within_bounds(row_date, start_value, end_value)


def _coerce_bound(value: datetime | None) -> date | None:
    return _coerce_date(value) if value else None


def _within_bounds(value: date, start: date | None, end: date | None) -> bool:
    return (start is None or value >= start) and (end is None or value <= end)


def _extract_date(row: Mapping[str, object]) -> date | None:
    for key in ("created_at", "played_at", "trend_date"):
        value = row.get(key)
        date_value = _coerce_date(value)
        if date_value is not None:
            return date_value
    return None


def _coerce_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None
