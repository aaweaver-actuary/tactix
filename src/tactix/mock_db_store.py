from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import cast

from tactix.base_db_store import BaseDbStore, BaseDbStoreContext


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
        source: str | None = None,
        motif: str | None = None,
        rating_bucket: str | None = None,
        time_control: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, object]:
        payload = dict(self._payload)
        normalized_source = None if source in (None, "all") else source
        payload["source"] = normalized_source or "all"
        payload["user"] = self.settings.user
        payload["metrics"] = _filter_rows(
            payload.get("metrics", []),
            source=normalized_source,
            motif=motif,
            rating_bucket=rating_bucket,
            time_control=time_control,
            start_date=start_date,
            end_date=end_date,
        )
        payload["recent_games"] = _filter_rows(
            payload.get("recent_games", []),
            source=normalized_source,
            motif=motif,
            rating_bucket=rating_bucket,
            time_control=time_control,
            start_date=start_date,
            end_date=end_date,
        )
        payload["positions"] = _filter_rows(
            payload.get("positions", []),
            source=normalized_source,
            motif=motif,
            rating_bucket=rating_bucket,
            time_control=time_control,
            start_date=start_date,
            end_date=end_date,
        )
        payload["tactics"] = _filter_rows(
            payload.get("tactics", []),
            source=normalized_source,
            motif=motif,
            rating_bucket=rating_bucket,
            time_control=time_control,
            start_date=start_date,
            end_date=end_date,
        )
        return payload


def _filter_rows(
    rows: Iterable[object],
    *,
    source: str | None,
    motif: str | None,
    rating_bucket: str | None,
    time_control: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> list[object]:
    filtered: list[object] = []
    for row in rows:
        if not isinstance(row, dict):
            filtered.append(row)
            continue
        row_dict = cast(Mapping[str, object], row)
        if not _row_matches_filters(
            row_dict,
            source=source,
            motif=motif,
            rating_bucket=rating_bucket,
            time_control=time_control,
            start_date=start_date,
            end_date=end_date,
        ):
            continue
        filtered.append(row)
    return filtered


def _row_matches_filters(
    row: Mapping[str, object],
    *,
    source: str | None,
    motif: str | None,
    rating_bucket: str | None,
    time_control: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> bool:
    return all(
        (
            _matches_value(row, "source", source),
            _matches_value(row, "motif", motif),
            _matches_value(row, "rating_bucket", rating_bucket),
            _matches_value(row, "time_control", time_control),
            _matches_date_range(row, start_date, end_date),
        )
    )


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
