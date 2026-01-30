from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, Mapping, cast

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
        if not _matches_value(row_dict, "source", source):
            continue
        if not _matches_value(row_dict, "motif", motif):
            continue
        if not _matches_value(row_dict, "rating_bucket", rating_bucket):
            continue
        if not _matches_value(row_dict, "time_control", time_control):
            continue
        if not _matches_date_range(row_dict, start_date, end_date):
            continue
        filtered.append(row)
    return filtered


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
    if row_date is None:
        return True
    start_value = _coerce_date(start_date) if start_date is not None else None
    if start_value is not None and row_date < start_value:
        return False
    end_value = _coerce_date(end_date) if end_date is not None else None
    if end_value is not None and row_date > end_value:
        return False
    return True


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
