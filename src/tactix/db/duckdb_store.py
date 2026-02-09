"""DuckDB-backed data store implementation."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import duckdb

from tactix.dashboard_query import (
    DashboardQuery,
    clone_dashboard_query,
    resolve_dashboard_query,
)
from tactix.db._build_legacy_raw_pgn_inserts import _build_legacy_raw_pgn_inserts
from tactix.db._drop_table_if_exists import _drop_table_if_exists
from tactix.db._migration_add_columns import _migration_add_columns
from tactix.db._migration_add_games_table import _migration_add_games_table
from tactix.db._migration_add_pipeline_views import _migration_add_pipeline_views
from tactix.db._migration_add_position_legality import _migration_add_position_legality
from tactix.db._migration_add_tactic_explanations import _migration_add_tactic_explanations
from tactix.db._migration_add_tactic_metadata import _migration_add_tactic_metadata
from tactix.db._migration_add_training_attempt_latency import (
    _migration_add_training_attempt_latency,
)
from tactix.db._migration_add_user_moves_view import _migration_add_user_moves_view
from tactix.db._migration_base_tables import _migration_base_tables
from tactix.db._migration_raw_pgns_versioning import _migration_raw_pgns_versioning
from tactix.db.duckdb_dashboard_reader import (
    DuckDbDashboardDependencies,
    DuckDbDashboardFetchers,
    DuckDbDashboardReader,
)
from tactix.db.duckdb_dashboard_repository import (
    DuckDbDashboardRepository,
    default_dashboard_repository_dependencies,
)
from tactix.define_base_db_store__db_store import BaseDbStore
from tactix.define_base_db_store_context__db_store import BaseDbStoreContext

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
    position_id BIGINT,
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
    tactic_piece TEXT,
    mate_type TEXT,
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

SCHEMA_VERSION = 10


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


def _dashboard_repository(conn: duckdb.DuckDBPyConnection) -> DuckDbDashboardRepository:
    return DuckDbDashboardRepository(
        conn,
        dependencies=default_dashboard_repository_dependencies(),
    )


def _wrap_dashboard_fetcher(fetcher: Callable[..., list[dict[str, object]]]):
    def _fetcher(
        _conn: duckdb.DuckDBPyConnection,
        dashboard_query: DashboardQuery,
        **kwargs: object,
    ) -> list[dict[str, object]]:
        return fetcher(dashboard_query, **kwargs)

    return _fetcher


def _build_dashboard_fetchers(
    repository: DuckDbDashboardRepository,
) -> DuckDbDashboardFetchers:
    return DuckDbDashboardFetchers(
        metrics=_wrap_dashboard_fetcher(repository.fetch_metrics),
        recent_games=_wrap_dashboard_fetcher(repository.fetch_recent_games),
        recent_positions=_wrap_dashboard_fetcher(repository.fetch_recent_positions),
        recent_tactics=_wrap_dashboard_fetcher(repository.fetch_recent_tactics),
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

        reader = DuckDbDashboardReader(
            conn,
            user=self.settings.user,
            dependencies=DuckDbDashboardDependencies(
                resolve_query=resolve_dashboard_query,
                clone_query=clone_dashboard_query,
                fetchers=_build_dashboard_fetchers(repository),
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
    (8, _migration_add_games_table),
    (9, _migration_add_tactic_metadata),
    (10, _migration_add_user_moves_view),
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


_VULTURE_USED = (SCHEMA_VERSION, _ensure_column)
