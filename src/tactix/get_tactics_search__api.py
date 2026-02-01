from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import Query

from tactix.coerce_date_to_datetime__datetime import _coerce_date_to_datetime
from tactix.config import get_settings
from tactix.db.duckdb_store import fetch_recent_tactics, get_connection, init_schema
from tactix.normalize_source__source import _normalize_source


def tactics_search(
    source: Annotated[str | None, Query()] = None,
    motif: Annotated[str | None, Query()] = None,
    rating_bucket: Annotated[str | None, Query()] = None,
    time_control: Annotated[str | None, Query()] = None,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    limit: int = Query(20, ge=1, le=200),
) -> dict[str, object]:
    normalized_source = _normalize_source(source)
    settings = get_settings(source=normalized_source)
    start_datetime = _coerce_date_to_datetime(start_date)
    end_datetime = _coerce_date_to_datetime(end_date, end_of_day=True)
    conn = get_connection(settings.duckdb_path)
    init_schema(conn)
    tactics = fetch_recent_tactics(
        conn,
        limit=limit,
        source=normalized_source,
        motif=motif,
        rating_bucket=rating_bucket,
        time_control=time_control,
        start_date=start_datetime,
        end_date=end_datetime,
    )
    response_source = "all" if normalized_source is None else normalized_source
    return {"source": response_source, "limit": limit, "tactics": tactics}
