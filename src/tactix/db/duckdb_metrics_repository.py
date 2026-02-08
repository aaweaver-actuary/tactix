"""Metrics repository for DuckDB-backed storage."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

import duckdb

from tactix.db._rows_to_dicts import _rows_to_dicts
from tactix.db.duckdb_store import init_schema
from tactix.db.raw_pgns_queries import latest_raw_pgns_query
from tactix.utils.to_int import to_int


@dataclass(frozen=True)
class DuckDbMetricsDependencies:
    """Dependencies used by the metrics repository."""

    init_schema: Callable[[duckdb.DuckDBPyConnection], None]
    latest_raw_pgns_query: Callable[[], str]
    rows_to_dicts: Callable[[duckdb.DuckDBPyRelation], list[dict[str, object]]]


class DuckDbMetricsRepository:
    """Encapsulates metrics summary updates for DuckDB."""

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        *,
        dependencies: DuckDbMetricsDependencies,
    ) -> None:
        self._conn = conn
        self._dependencies = dependencies

    def update_metrics_summary(self) -> None:
        """Recompute metrics summary rows."""
        deps = self._dependencies
        deps.init_schema(self._conn)
        self._conn.execute("DELETE FROM metrics_summary")
        metric_rows = self.build_metrics_summary_rows()
        if not metric_rows:
            return
        self._conn.executemany(
            """
            INSERT INTO metrics_summary (
                source,
                metric_type,
                motif,
                window_days,
                trend_date,
                rating_bucket,
                time_control,
                total,
                found,
                missed,
                failed_attempt,
                unclear,
                found_rate,
                miss_rate,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            metric_rows,
        )

    def build_metrics_summary_rows(self) -> list[tuple[object, ...]]:
        """Return metrics summary rows computed from current inputs."""
        return _build_metrics_summary_rows(self._conn, self._dependencies)


def default_metrics_dependencies() -> DuckDbMetricsDependencies:
    """Return default dependency wiring for DuckDB metrics operations."""
    return DuckDbMetricsDependencies(
        init_schema=init_schema,
        latest_raw_pgns_query=latest_raw_pgns_query,
        rows_to_dicts=_rows_to_dicts,
    )


def _coerce_metric_count(value: object) -> int:
    """Coerce metric counts into integers."""
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return int(value)
    parsed = to_int(value)
    return parsed if parsed is not None else 0


def _coerce_metric_rate(value: object, numerator: int, denominator: int) -> float | None:
    """Coerce metric rates into floats."""
    if isinstance(value, (int, float)):
        return float(value)
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _rating_bucket_for_rating(rating: int | None) -> str | None:
    """Return the rating bucket label for a rating."""
    if rating is None:
        return "unknown"
    bucket_size = 200
    start = (rating // bucket_size) * bucket_size
    end = start + bucket_size - 1
    return f"{start}-{end}"


def _build_metrics_summary_rows(
    conn: duckdb.DuckDBPyConnection,
    deps: DuckDbMetricsDependencies,
) -> list[tuple[object, ...]]:
    rows = _fetch_metric_inputs(conn, deps)
    if not rows:
        return []
    metrics: list[tuple[object, ...]] = []
    metrics.extend(_build_motif_breakdowns(rows))
    metrics.extend(_build_trend_rows(rows, window_days=7))
    metrics.extend(_build_trend_rows(rows, window_days=30))
    metrics.extend(_build_time_trouble_rows(rows))
    return metrics


def _fetch_metric_inputs(
    conn: duckdb.DuckDBPyConnection,
    deps: DuckDbMetricsDependencies,
) -> list[dict[str, object]]:
    latest_query = deps.latest_raw_pgns_query()
    result = conn.execute(
        f"""
        WITH latest_pgns AS (
            {latest_query}
        )
        SELECT
            t.game_id,
            t.motif,
            COALESCE(o.result, 'unclear') AS result,
            p.source,
            p.clock_seconds,
            p.created_at,
            r.user_rating,
            r.time_control,
            r.last_timestamp_ms
        FROM tactics t
        LEFT JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
        LEFT JOIN positions p ON p.position_id = t.position_id
        LEFT JOIN latest_pgns r ON r.game_id = p.game_id AND r.source = p.source
        """
    )
    raw_rows = deps.rows_to_dicts(result)
    for row in raw_rows:
        rating = row.get("user_rating")
        row["rating_bucket"] = _rating_bucket_for_rating(
            int(rating) if rating is not None else None
        )
        row["trend_date"] = _trend_date_from_row(row)
    return raw_rows


def _trend_date_from_row(row: Mapping[str, object]) -> datetime.date | None:
    timestamp_ms = row.get("last_timestamp_ms")
    if isinstance(timestamp_ms, (int, float)) and timestamp_ms > 0:
        return datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=UTC).date()
    created_at = row.get("created_at")
    if isinstance(created_at, datetime):
        return created_at.date()
    return None


def _count_result_types(items: list[dict[str, object]]) -> dict[str, int]:
    counts = {
        "found": 0,
        "missed": 0,
        "failed_attempt": 0,
        "unclear": 0,
    }
    for item in items:
        result = item.get("result")
        if isinstance(result, str) and result in counts:
            counts[result] += 1
    return counts


def _window_rate(values: list[int], idx: int, window_days: int) -> float:
    start = max(0, idx - window_days + 1)
    window = values[start : idx + 1]
    return sum(window) / len(window) if window else 0.0


def _sorted_trend_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        items,
        key=lambda item: (
            item.get("last_timestamp_ms") or 0,
            item.get("created_at") or datetime.min.replace(tzinfo=UTC),
        ),
    )


def _result_flag(item: dict[str, object], expected: str) -> int:
    return 1 if item.get("result") == expected else 0


def _build_trend_row(
    group: tuple[object, object, object, object],
    item: dict[str, object],
    window_days: int,
    found_rate: float,
    miss_rate: float,
) -> tuple[object, ...]:
    source, motif, rating_bucket, time_control = group
    result = item.get("result")
    return (
        source,
        "trend",
        motif,
        window_days,
        item.get("trend_date"),
        rating_bucket,
        time_control,
        1,
        1 if result == "found" else 0,
        1 if result == "missed" else 0,
        1 if result == "failed_attempt" else 0,
        1 if result == "unclear" else 0,
        found_rate,
        miss_rate,
    )


def _build_trend_rows_for_group(
    group: tuple[object, object, object, object],
    items: list[dict[str, object]],
    window_days: int,
) -> list[tuple[object, ...]]:
    sorted_items = _sorted_trend_items(items)
    results = [_result_flag(item, "found") for item in sorted_items]
    misses = [_result_flag(item, "missed") for item in sorted_items]
    metric_rows: list[tuple[object, ...]] = []
    for idx, item in enumerate(sorted_items):
        found_rate = _window_rate(results, idx, window_days)
        miss_rate = _window_rate(misses, idx, window_days)
        metric_rows.append(_build_trend_row(group, item, window_days, found_rate, miss_rate))
    return metric_rows


def _is_time_trouble_item(item: dict[str, object], threshold: int) -> bool:
    clock_seconds = item.get("clock_seconds")
    if clock_seconds is None:
        return False
    if not isinstance(clock_seconds, (int, float)):
        return False
    return clock_seconds <= threshold


def _split_time_trouble_items(
    items: list[dict[str, object]],
    threshold: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    trouble_items = [item for item in items if _is_time_trouble_item(item, threshold)]
    safe_items = [item for item in items if item not in trouble_items]
    return trouble_items, safe_items


def _count_found(items: list[dict[str, object]]) -> int:
    return sum(1 for item in items if item.get("result") == "found")


def _group_metric_rows(
    rows: list[dict[str, object]],
) -> dict[tuple[object, object, object, object], list[dict[str, object]]]:
    grouped: dict[
        tuple[object, object, object, object],
        list[dict[str, object]],
    ] = defaultdict(list)
    for row in rows:
        grouped[
            (
                row.get("source"),
                row.get("motif"),
                row.get("rating_bucket"),
                row.get("time_control"),
            )
        ].append(row)
    return grouped


def _build_motif_breakdowns(rows: list[dict[str, object]]) -> list[tuple[object, ...]]:
    grouped = _group_metric_rows(rows)
    metric_rows: list[tuple[object, ...]] = []
    for (source, motif, rating_bucket, time_control), items in grouped.items():
        total = len(items)
        counts = _count_result_types(items)
        found_rate = _coerce_metric_rate(None, counts["found"], total)
        miss_rate = _coerce_metric_rate(None, counts["missed"], total)
        metric_rows.append(
            (
                source,
                "motif_breakdown",
                motif,
                0,
                None,
                rating_bucket,
                time_control,
                total,
                counts["found"],
                counts["missed"],
                counts["failed_attempt"],
                counts["unclear"],
                found_rate,
                miss_rate,
            )
        )
    return metric_rows


def _build_trend_rows(
    rows: list[dict[str, object]],
    *,
    window_days: int,
) -> list[tuple[object, ...]]:
    grouped = _group_metric_rows(rows)
    metric_rows: list[tuple[object, ...]] = []
    for (source, motif, rating_bucket, time_control), items in grouped.items():
        metric_rows.extend(
            _build_trend_rows_for_group(
                (source, motif, rating_bucket, time_control),
                items=items,
                window_days=window_days,
            )
        )
    return metric_rows


def _build_time_trouble_rows(rows: list[dict[str, object]]) -> list[tuple[object, ...]]:
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = (row.get("source"), row.get("time_control"))
        grouped[key].append(row)
    metric_rows: list[tuple[object, ...]] = []
    for (source, time_control), items in grouped.items():
        metric_rows.append(_build_time_trouble_row(source, time_control, items))
    return metric_rows


def _build_time_trouble_row(
    source: object,
    time_control: object,
    items: list[dict[str, object]],
) -> tuple[object, ...]:
    total = len(items)
    counts = _count_result_types(items)
    miss_rate = _coerce_metric_rate(None, counts["missed"], total)
    trouble_threshold = 30
    trouble_items, safe_items = _split_time_trouble_items(items, trouble_threshold)
    trouble_found = _count_found(trouble_items)
    safe_found = _count_found(safe_items)
    trouble_rate = trouble_found / len(trouble_items) if trouble_items else 0.0
    safe_rate = safe_found / len(safe_items) if safe_items else 0.0
    found_rate = safe_rate - trouble_rate
    return (
        source,
        "time_trouble_correlation",
        None,
        0,
        None,
        None,
        time_control,
        total,
        counts["found"],
        counts["missed"],
        counts["failed_attempt"],
        counts["unclear"],
        found_rate,
        miss_rate,
    )


_VULTURE_USED = (_coerce_metric_count,)
