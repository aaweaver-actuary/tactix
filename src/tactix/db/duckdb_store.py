"""DuckDB-backed data store implementation."""

from __future__ import annotations

import os
from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from tactix.dashboard_query import (
    DashboardQuery,
    clone_dashboard_query,
)
from tactix.db._build_legacy_raw_pgn_inserts import _build_legacy_raw_pgn_inserts
from tactix.db._drop_table_if_exists import _drop_table_if_exists
from tactix.db._migration_add_columns import _migration_add_columns
from tactix.db._migration_add_pipeline_views import _migration_add_pipeline_views
from tactix.db._migration_add_position_legality import _migration_add_position_legality
from tactix.db._migration_add_tactic_explanations import _migration_add_tactic_explanations
from tactix.db._migration_add_training_attempt_latency import (
    _migration_add_training_attempt_latency,
)
from tactix.db._migration_base_tables import _migration_base_tables
from tactix.db._migration_raw_pgns_versioning import _migration_raw_pgns_versioning
from tactix.db._resolve_dashboard_query import _resolve_dashboard_query
from tactix.db._rows_to_dicts import _rows_to_dicts
from tactix.db.duckdb_dashboard_reader import (
    DuckDbDashboardDependencies,
    DuckDbDashboardFetchers,
    DuckDbDashboardReader,
)
from tactix.db.duckdb_dashboard_repository import (
    DuckDbDashboardRepository,
    default_dashboard_repository_dependencies,
)
from tactix.db.duckdb_position_repository import (
    DuckDbPositionRepository,
    default_position_dependencies,
)
from tactix.db.duckdb_tactic_repository import (
    DuckDbTacticRepository,
    default_tactic_dependencies,
)
from tactix.db.fetch_unanalyzed_positions import (
    fetch_unanalyzed_positions as _fetch_unanalyzed_positions,
)
from tactix.db.raw_pgns_queries import latest_raw_pgns_query
from tactix.db.record_training_attempt import record_training_attempt as _record_training_attempt
from tactix.define_base_db_store__db_store import BaseDbStore
from tactix.define_base_db_store_context__db_store import BaseDbStoreContext
from tactix.utils.to_int import to_int

RAW_PGNS_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_pgns (
    raw_pgn_id BIGINT PRIMARY KEY,
    game_id TEXT,
    user TEXT,
    source TEXT,
    fetched_at TIMESTAMP,
    pgn TEXT,
    pgn_hash TEXT,
    pgn_version INTEGER,
    user_rating INTEGER,
    time_control TEXT,
    ingested_at TIMESTAMP,
    last_timestamp_ms BIGINT,
    cursor TEXT
);
"""

POSITIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
    position_id BIGINT PRIMARY KEY,
    game_id TEXT,
    user TEXT,
    source TEXT,
    fen TEXT,
    ply INTEGER,
    move_number INTEGER,
    side_to_move TEXT,
    user_to_move BOOLEAN DEFAULT TRUE,
    uci TEXT,
    san TEXT,
    clock_seconds DOUBLE,
    is_legal BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

TACTICS_SCHEMA = """
CREATE TABLE IF NOT EXISTS tactics (
    tactic_id BIGINT PRIMARY KEY,
    game_id TEXT,
    position_id BIGINT,
    motif TEXT,
    severity DOUBLE,
    best_uci TEXT,
    best_san TEXT,
    explanation TEXT,
    eval_cp INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

TACTIC_OUTCOMES_SCHEMA = """
CREATE TABLE IF NOT EXISTS tactic_outcomes (
    outcome_id BIGINT PRIMARY KEY,
    tactic_id BIGINT,
    result TEXT,
    user_uci TEXT,
    eval_delta INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

METRICS_VERSION_SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics_version (
    version BIGINT,
    updated_at TIMESTAMP
);
"""

METRICS_SUMMARY_SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics_summary (
    source TEXT,
    metric_type TEXT,
    motif TEXT,
    window_days INTEGER,
    trend_date DATE,
    rating_bucket TEXT,
    time_control TEXT,
    total BIGINT,
    found BIGINT,
    missed BIGINT,
    failed_attempt BIGINT,
    unclear BIGINT,
    found_rate DOUBLE,
    miss_rate DOUBLE,
    updated_at TIMESTAMP
);
"""

TRAINING_ATTEMPTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS training_attempts (
    attempt_id BIGINT PRIMARY KEY,
    tactic_id BIGINT,
    position_id BIGINT,
    source TEXT,
    attempted_uci TEXT,
    correct BOOLEAN,
    success BOOLEAN,
    best_uci TEXT,
    motif TEXT,
    severity DOUBLE,
    eval_delta INTEGER,
    latency_ms BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

SCHEMA_VERSION_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER,
    updated_at TIMESTAMP
);
"""

SCHEMA_VERSION = 7


def fetch_unanalyzed_positions(
    conn: duckdb.DuckDBPyConnection,
    game_ids: list[str] | None = None,
    source: str | None = None,
    limit: int | None = None,
) -> list[dict[str, object]]:
    """Return positions that have not yet been analyzed."""
    return _fetch_unanalyzed_positions(
        conn,
        game_ids=game_ids,
        source=source,
        limit=limit,
    )


def record_training_attempt(
    conn: duckdb.DuckDBPyConnection,
    payload: Mapping[str, object],
) -> int:
    """Persist a training attempt record."""
    return _record_training_attempt(conn, payload)


def _should_attempt_wal_recovery(exc: BaseException) -> bool:
    """Return True when WAL recovery is allowed for the given exception."""
    message = str(exc).lower()
    if "wal replay failed" not in message and "wal error" not in message:
        return False
    return (
        bool(os.environ.get("PYTEST_CURRENT_TEST"))
        or os.environ.get("TACTIX_ENV", "").lower() == "dev"
        or os.environ.get("TACTIX_ALLOW_WAL_RECOVERY", "").lower() == "true"
    )


def get_connection(db_path: Path | str) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection, recovering from WAL errors when needed."""
    db_path = Path(db_path)
    try:
        return duckdb.connect(str(db_path))
    except duckdb.InternalException as exc:
        if _should_attempt_wal_recovery(exc):
            wal_paths = list(db_path.parent.glob("*.wal"))
            if wal_paths:
                for wal_path in wal_paths:
                    wal_path.unlink()
                return duckdb.connect(str(db_path))
        raise


def get_schema_version(conn: duckdb.DuckDBPyConnection) -> int:
    """Return the current schema version."""
    conn.execute(SCHEMA_VERSION_SCHEMA)
    row = conn.execute(
        "SELECT version FROM schema_version ORDER BY updated_at DESC LIMIT 1"
    ).fetchone()
    return int(row[0]) if row else 0


def migrate_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Run schema migrations to the latest version."""
    conn.execute(SCHEMA_VERSION_SCHEMA)
    _ensure_raw_pgns_versioned(conn)
    current_version = get_schema_version(conn)
    for version, migration in _SCHEMA_MIGRATIONS:
        if version <= current_version:
            continue
        migration(conn)
        conn.execute(
            "INSERT INTO schema_version (version, updated_at) VALUES (?, CURRENT_TIMESTAMP)",
            [version],
        )


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure all required tables exist and migrations are applied."""
    migrate_schema(conn)


def _get_raw_pgn_columns(conn: duckdb.DuckDBPyConnection) -> set[str]:
    try:
        return {row[1] for row in conn.execute("PRAGMA table_info('raw_pgns')").fetchall()}
    except duckdb.Error:
        return set()


def _ensure_raw_pgns_versioned(conn: duckdb.DuckDBPyConnection) -> None:
    """Ensure raw PGN rows include versioning columns."""
    columns = _get_raw_pgn_columns(conn)
    if not columns:
        return
    if "raw_pgn_id" not in columns or "pgn_version" not in columns:
        _migrate_raw_pgns_legacy(conn)


def _rating_bucket_for_rating(rating: int | None) -> str | None:
    """Return the rating bucket label for a rating."""
    if rating is None:
        return "unknown"
    bucket_size = 200
    start = (rating // bucket_size) * bucket_size
    end = start + bucket_size - 1
    return f"{start}-{end}"


def _position_repository(conn: duckdb.DuckDBPyConnection) -> DuckDbPositionRepository:
    return DuckDbPositionRepository(conn, dependencies=default_position_dependencies())


def _tactic_repository(conn: duckdb.DuckDBPyConnection) -> DuckDbTacticRepository:
    return DuckDbTacticRepository(conn, dependencies=default_tactic_dependencies())


def _dashboard_repository(conn: duckdb.DuckDBPyConnection) -> DuckDbDashboardRepository:
    return DuckDbDashboardRepository(
        conn,
        dependencies=default_dashboard_repository_dependencies(),
    )


class DuckDbStore(BaseDbStore):
    """DuckDB-backed store implementation."""

    def __init__(self, context: BaseDbStoreContext, db_path: Path | None = None) -> None:
        super().__init__(context)
        self._db_path = db_path or context.settings.duckdb_path

    @property
    def db_path(self) -> Path:
        return self._db_path

    def get_dashboard_payload(
        self,
        query: DashboardQuery | str | None = None,
        *,
        filters: DashboardQuery | None = None,
        **legacy: object,
    ) -> dict[str, object]:
        conn = get_connection(self._db_path)
        repository = _dashboard_repository(conn)

        def _metrics_fetcher(
            _conn: duckdb.DuckDBPyConnection,
            dashboard_query: DashboardQuery,
            **kwargs: object,
        ) -> list[dict[str, object]]:
            return repository.fetch_metrics(dashboard_query, **kwargs)

        def _recent_games_fetcher(
            _conn: duckdb.DuckDBPyConnection,
            dashboard_query: DashboardQuery,
            **kwargs: object,
        ) -> list[dict[str, object]]:
            return repository.fetch_recent_games(dashboard_query, **kwargs)

        def _recent_positions_fetcher(
            _conn: duckdb.DuckDBPyConnection,
            dashboard_query: DashboardQuery,
            **kwargs: object,
        ) -> list[dict[str, object]]:
            return repository.fetch_recent_positions(dashboard_query, **kwargs)

        def _recent_tactics_fetcher(
            _conn: duckdb.DuckDBPyConnection,
            dashboard_query: DashboardQuery,
            **kwargs: object,
        ) -> list[dict[str, object]]:
            return repository.fetch_recent_tactics(dashboard_query, **kwargs)

        reader = DuckDbDashboardReader(
            conn,
            user=self.settings.user,
            dependencies=DuckDbDashboardDependencies(
                resolve_query=_resolve_dashboard_query,
                clone_query=clone_dashboard_query,
                fetchers=DuckDbDashboardFetchers(
                    metrics=_metrics_fetcher,
                    recent_games=_recent_games_fetcher,
                    recent_positions=_recent_positions_fetcher,
                    recent_tactics=_recent_tactics_fetcher,
                ),
                fetch_version=fetch_version,
                init_schema=init_schema,
            ),
        )
        return reader.get_dashboard_payload(query, filters=filters, **legacy)


_SCHEMA_MIGRATIONS = [
    (1, _migration_base_tables),
    (2, _migration_raw_pgns_versioning),
    (3, _migration_add_columns),
    (4, _migration_add_training_attempt_latency),
    (5, _migration_add_position_legality),
    (6, _migration_add_tactic_explanations),
    (7, _migration_add_pipeline_views),
]


def _migrate_raw_pgns_legacy(conn: duckdb.DuckDBPyConnection) -> None:
    """Migrate legacy raw PGN tables into the versioned schema."""
    conn.execute("BEGIN TRANSACTION")
    try:
        _drop_table_if_exists(conn, "raw_pgns_legacy")
        conn.execute("ALTER TABLE raw_pgns RENAME TO raw_pgns_legacy")
        conn.execute(RAW_PGNS_SCHEMA)
        legacy_rows = conn.execute(
            """
            SELECT game_id, user, source, fetched_at, pgn, last_timestamp_ms, cursor
            FROM raw_pgns_legacy
            """
        ).fetchall()
        inserts = _build_legacy_raw_pgn_inserts(legacy_rows)
        if inserts:
            conn.executemany(
                """
                INSERT INTO raw_pgns (
                    raw_pgn_id,
                    game_id,
                    user,
                    source,
                    fetched_at,
                    pgn,
                    pgn_hash,
                    pgn_version,
                    user_rating,
                    time_control,
                    ingested_at,
                    last_timestamp_ms,
                    cursor
                )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                inserts,
            )
        conn.execute("DROP TABLE raw_pgns_legacy")
        conn.execute("COMMIT")
    except duckdb.Error:
        conn.execute("ROLLBACK")
        raise


def _ensure_column(
    conn: duckdb.DuckDBPyConnection, table: str, column: str, definition: str
) -> None:
    """Add a column to a table when missing."""
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info('{table}')").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def fetch_position_counts(
    conn: duckdb.DuckDBPyConnection,
    game_ids: list[str],
    source: str | None,
) -> dict[str, int]:
    """Return position counts keyed by game id."""
    return _position_repository(conn).fetch_position_counts(game_ids, source)


def fetch_positions_for_games(
    conn: duckdb.DuckDBPyConnection,
    game_ids: list[str],
) -> list[dict[str, object]]:
    """Return stored positions for the provided games."""
    return _position_repository(conn).fetch_positions_for_games(game_ids)


def insert_positions(
    conn: duckdb.DuckDBPyConnection,
    positions: list[Mapping[str, object]],
) -> list[int]:
    """Insert position rows and return new ids."""
    return _position_repository(conn).insert_positions(positions)


def insert_tactics(
    conn: duckdb.DuckDBPyConnection,
    rows: list[Mapping[str, object]],
) -> list[int]:
    """Insert tactic rows and return ids."""
    return _tactic_repository(conn).insert_tactics(rows)


def insert_tactic_outcomes(
    conn: duckdb.DuckDBPyConnection,
    rows: list[Mapping[str, object]],
) -> list[int]:
    """Insert tactic outcome rows and return ids."""
    return _tactic_repository(conn).insert_tactic_outcomes(rows)


def upsert_tactic_with_outcome(
    conn: duckdb.DuckDBPyConnection,
    tactic_row: Mapping[str, object],
    outcome_row: Mapping[str, object],
) -> int:
    """Insert a tactic with its outcome and return the tactic id."""
    return _tactic_repository(conn).upsert_tactic_with_outcome(tactic_row, outcome_row)


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


def update_metrics_summary(conn: duckdb.DuckDBPyConnection) -> None:
    """Recompute metrics summary rows."""
    init_schema(conn)
    conn.execute("DELETE FROM metrics_summary")
    metric_rows = _build_metrics_summary_rows(conn)
    if not metric_rows:
        return
    conn.executemany(
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


def _build_metrics_summary_rows(
    conn: duckdb.DuckDBPyConnection,
) -> list[tuple[object, ...]]:
    rows = _fetch_metric_inputs(conn)
    if not rows:
        return []
    metrics: list[tuple[object, ...]] = []
    metrics.extend(_build_motif_breakdowns(rows))
    metrics.extend(_build_trend_rows(rows, window_days=7))
    metrics.extend(_build_trend_rows(rows, window_days=30))
    metrics.extend(_build_time_trouble_rows(rows))
    return metrics


def _fetch_metric_inputs(conn: duckdb.DuckDBPyConnection) -> list[dict[str, object]]:
    latest_query = latest_raw_pgns_query()
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
    raw_rows = _rows_to_dicts(result)
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


def write_metrics_version(conn: duckdb.DuckDBPyConnection) -> int:
    """Increment and persist the metrics version."""
    current = fetch_version(conn)
    new_version = current + 1
    conn.execute(
        "INSERT INTO metrics_version (version, updated_at) VALUES (?, CURRENT_TIMESTAMP)",
        [new_version],
    )
    return new_version


def fetch_version(conn: duckdb.DuckDBPyConnection) -> int:
    """Fetch the latest metrics version."""
    version_row = conn.execute("SELECT MAX(version) FROM metrics_version").fetchone()
    if not version_row or version_row[0] is None:
        return 0
    return int(version_row[0])


_VULTURE_USED = (SCHEMA_VERSION, _ensure_column, _coerce_metric_count)
