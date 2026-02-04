"""DuckDB-backed data store implementation."""

from __future__ import annotations

import os
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import chess.pgn
import duckdb

from tactix._get_game_result_for_user_from_pgn_headers import (
    _get_game_result_for_user_from_pgn_headers,
)
from tactix.base_db_store import BaseDbStore, BaseDbStoreContext
from tactix.dashboard_query import (
    DashboardQuery,
    clone_dashboard_query,
)
from tactix.db._append_date_range_filters import _append_date_range_filters
from tactix.db._append_optional_filter import _append_optional_filter
from tactix.db._append_time_control_filter import _append_time_control_filter
from tactix.db._build_legacy_raw_pgn_inserts import _build_legacy_raw_pgn_inserts
from tactix.db._build_raw_pgn_upsert_plan import _build_raw_pgn_upsert_plan
from tactix.db._drop_table_if_exists import _drop_table_if_exists
from tactix.db._fetch_next_raw_pgn_id import _fetch_next_raw_pgn_id
from tactix.db._insert_raw_pgn_plan import _insert_raw_pgn_plan
from tactix.db._migration_add_columns import _migration_add_columns
from tactix.db._migration_add_pipeline_views import _migration_add_pipeline_views
from tactix.db._migration_add_position_legality import _migration_add_position_legality
from tactix.db._migration_add_tactic_explanations import _migration_add_tactic_explanations
from tactix.db._migration_add_training_attempt_latency import (
    _migration_add_training_attempt_latency,
)
from tactix.db._migration_base_tables import _migration_base_tables
from tactix.db._migration_raw_pgns_versioning import _migration_raw_pgns_versioning
from tactix.db._normalize_filter import _normalize_filter
from tactix.db._rating_bucket_clause import _rating_bucket_clause
from tactix.db._resolve_dashboard_query import _resolve_dashboard_query
from tactix.db._rows_to_dicts import _rows_to_dicts
from tactix.db.fetch_latest_raw_pgns import fetch_latest_raw_pgns as _fetch_latest_raw_pgns
from tactix.db.fetch_unanalyzed_positions import (
    fetch_unanalyzed_positions as _fetch_unanalyzed_positions,
)
from tactix.db.raw_pgn_summary import (
    build_raw_pgn_summary_payload,
    coerce_raw_pgn_summary_rows,
)
from tactix.db.raw_pgns_queries import latest_raw_pgns_query
from tactix.db.RawPgnInsertInputs import RawPgnInsertInputs
from tactix.db.record_training_attempt import record_training_attempt
from tactix.extract_pgn_metadata import extract_pgn_metadata
from tactix.format_tactics__explanation import format_tactic_explanation
from tactix.sql_tactics import (
    OUTCOME_COLUMNS,
    TACTIC_ANALYSIS_COLUMNS,
    TACTIC_COLUMNS,
    TACTIC_QUEUE_COLUMNS,
)
from tactix.utils.logger import Logger
from tactix.utils.to_int import to_int

logger = Logger(__name__)


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


def hash_pgn(pgn: str) -> str:
    """Return the canonical hash for PGN content."""
    return BaseDbStore.hash_pgn(pgn)


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
        query = _resolve_dashboard_query(query, filters=filters, **legacy)
        conn = get_connection(self._db_path)
        init_schema(conn)
        active_source = None if query.source in (None, "all") else query.source
        response_source = "all" if active_source is None else active_source
        metrics_query = clone_dashboard_query(
            query,
            source=active_source,
            motif=query.motif,
        )
        non_motif_query = clone_dashboard_query(
            query,
            source=active_source,
            motif=None,
        )
        tactics_query = clone_dashboard_query(
            query,
            source=active_source,
            motif=query.motif,
        )
        return {
            "source": response_source,
            "user": self.settings.user,
            "metrics": fetch_metrics(
                conn,
                metrics_query,
            ),
            "recent_games": fetch_recent_games(
                conn,
                non_motif_query,
                user=self.settings.user,
            ),
            "positions": fetch_recent_positions(
                conn,
                non_motif_query,
            ),
            "tactics": fetch_recent_tactics(
                conn,
                tactics_query,
            ),
            "metrics_version": fetch_version(conn),
        }


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


def upsert_raw_pgns(
    conn: duckdb.DuckDBPyConnection,
    rows: Iterable[Mapping[str, object]],
) -> int:
    """Insert raw PGN rows with version tracking."""
    rows_list = list(rows)
    if not rows_list:
        return 0
    conn.execute("BEGIN TRANSACTION")
    try:
        inserted = _upsert_raw_pgn_rows(conn, rows_list)
        conn.execute("COMMIT")
    except duckdb.Error:
        conn.execute("ROLLBACK")
        raise
    return inserted


def _upsert_raw_pgn_rows(
    conn: duckdb.DuckDBPyConnection,
    rows_list: list[Mapping[str, object]],
) -> int:
    """Insert raw PGN rows and return insert count."""
    next_id = _fetch_next_raw_pgn_id(conn)
    latest_cache: dict[tuple[str, str], tuple[str | None, int]] = {}
    inserted = 0
    for row in rows_list:
        game_id = str(row["game_id"])
        source = str(row["source"])
        plan = _build_raw_pgn_upsert_plan(conn, row, game_id, source, latest_cache)
        if plan is None:
            continue
        next_id += 1
        _insert_raw_pgn_plan(
            conn,
            RawPgnInsertInputs(
                raw_pgn_id=next_id,
                game_id=game_id,
                source=source,
                row=row,
                plan=plan,
            ),
        )
        latest_cache[(game_id, source)] = (plan.pgn_hash, plan.pgn_version)
        inserted += 1
    return inserted


def fetch_latest_pgn_hashes(
    conn: duckdb.DuckDBPyConnection,
    game_ids: list[str],
    source: str | None,
) -> dict[str, str]:
    """Fetch latest PGN hashes for the provided game ids."""
    if not game_ids:
        return {}
    placeholders = ", ".join(["?"] * len(game_ids))
    params: list[object] = list(game_ids)
    sql = f"""
        WITH latest_pgns AS (
            {latest_raw_pgns_query(f"WHERE game_id IN ({placeholders})")}
        )
        SELECT game_id, pgn_hash
        FROM latest_pgns
    """
    if source:
        sql += " WHERE source = ?"
        params.append(source)
    rows = conn.execute(sql, params).fetchall()
    return {str(game_id): str(pgn_hash) for game_id, pgn_hash in rows if pgn_hash}


def fetch_latest_raw_pgns(
    conn: duckdb.DuckDBPyConnection,
    source: str | None = None,
    limit: int | None = None,
) -> list[dict[str, object]]:
    """Fetch the latest raw PGN rows for a source."""
    return _fetch_latest_raw_pgns(conn, source, limit)


def fetch_raw_pgns_summary(
    conn: duckdb.DuckDBPyConnection,
    *,
    source: str | None = None,
) -> dict[str, object]:
    """Return raw PGN summary payload for the given source."""
    where_clause = ""
    params: list[object] = []
    if source:
        where_clause = "WHERE source = ?"
        params.append(source)
    sources_result = conn.execute(
        f"""
        SELECT
            source,
            COUNT(*) AS total_rows,
            COUNT(DISTINCT game_id) AS distinct_games,
            MAX(ingested_at) AS latest_ingested_at
        FROM raw_pgns
        {where_clause}
        GROUP BY source
        ORDER BY source
        """,
        params,
    )
    sources = _rows_to_dicts(sources_result)
    totals_result = conn.execute(
        f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT game_id) AS distinct_games,
            MAX(ingested_at) AS latest_ingested_at
        FROM raw_pgns
        {where_clause}
        """,
        params,
    )
    totals_row = totals_result.fetchone()
    totals_dict = {}
    if totals_row:
        columns = [desc[0] for desc in totals_result.description]
        totals_dict = dict(zip(columns, totals_row, strict=False))
    return build_raw_pgn_summary_payload(
        sources=coerce_raw_pgn_summary_rows(sources),
        totals=totals_dict,
    )


def fetch_pipeline_table_counts(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    filters: DashboardQuery | None = None,
    **legacy: object,
) -> dict[str, int]:
    """Return per-table counts for pipeline verification."""
    resolved = _resolve_dashboard_query(query, filters=filters, **legacy)
    sql, params = _build_games_filtered_query(resolved)
    sql += """
        SELECT
            (SELECT COUNT(*) FROM games_filtered) AS games,
            (
                SELECT COUNT(*)
                FROM positions p
                INNER JOIN games_filtered r
                    ON p.game_id = r.game_id AND p.source = r.source
            ) AS positions,
            (
                SELECT COUNT(*)
                FROM user_moves u
                INNER JOIN games_filtered r
                    ON u.game_id = r.game_id AND u.source = r.source
            ) AS user_moves,
            (
                SELECT COUNT(*)
                FROM opportunities o
                INNER JOIN games_filtered r
                    ON o.game_id = r.game_id AND o.source = r.source
            ) AS opportunities,
            (
                SELECT COUNT(*)
                FROM conversions c
                INNER JOIN games_filtered r
                    ON c.game_id = r.game_id AND c.source = r.source
            ) AS conversions,
            (
                SELECT COUNT(*)
                FROM practice_queue q
                INNER JOIN games_filtered r
                    ON q.game_id = r.game_id AND q.source = r.source
            ) AS practice_queue
    """
    result = conn.execute(sql, params)
    row = result.fetchone()
    if not row:
        return {
            "games": 0,
            "positions": 0,
            "user_moves": 0,
            "opportunities": 0,
            "conversions": 0,
            "practice_queue": 0,
        }
    columns = [desc[0] for desc in result.description]
    return {column: int(value or 0) for column, value in zip(columns, row, strict=False)}


def fetch_opportunity_motif_counts(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    filters: DashboardQuery | None = None,
    **legacy: object,
) -> dict[str, int]:
    """Return motif counts for opportunities in the dashboard range."""
    resolved = _resolve_dashboard_query(query, filters=filters, **legacy)
    sql, params = _build_games_filtered_query(resolved)
    sql += """
        SELECT o.motif, COUNT(*) AS total
        FROM opportunities o
        INNER JOIN games_filtered r
            ON o.game_id = r.game_id AND o.source = r.source
        GROUP BY o.motif
        ORDER BY o.motif
    """
    rows = _rows_to_dicts(conn.execute(sql, params))
    return {str(row.get("motif")): int(row.get("total") or 0) for row in rows}


def _build_games_filtered_query(
    resolved: DashboardQuery,
) -> tuple[str, list[object]]:
    sql = """
        WITH games_filtered AS (
            SELECT *
            FROM games r
    """
    params: list[object] = []
    conditions: list[str] = []
    if resolved.source:
        conditions.append("r.source = ?")
        params.append(resolved.source)
    _append_time_control_filter(conditions, params, resolved.time_control, "r.time_control")
    normalized_rating = _normalize_filter(resolved.rating_bucket)
    if normalized_rating:
        conditions.append(_rating_bucket_clause(normalized_rating))
    _append_date_range_filters(
        conditions,
        params,
        resolved.start_date,
        resolved.end_date,
        "to_timestamp(r.last_timestamp_ms / 1000)",
    )
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += """
        )
    """
    return sql, params


def fetch_position_counts(
    conn: duckdb.DuckDBPyConnection,
    game_ids: list[str],
    source: str | None,
) -> dict[str, int]:
    """Return position counts keyed by game id."""
    if not game_ids:
        return {}
    placeholders = ", ".join(["?"] * len(game_ids))
    params: list[object] = list(game_ids)
    sql = f"SELECT game_id, COUNT(*) FROM positions WHERE game_id IN ({placeholders})"
    if source:
        sql += " AND source = ?"
        params.append(source)
    sql += " GROUP BY game_id"
    rows = conn.execute(sql, params).fetchall()
    return {str(game_id): int(count) for game_id, count in rows}


def fetch_positions_for_games(
    conn: duckdb.DuckDBPyConnection,
    game_ids: list[str],
) -> list[dict[str, object]]:
    """Return stored positions for the provided games."""
    if not game_ids:
        return []
    placeholders = ", ".join(["?"] * len(game_ids))
    result = conn.execute(
        f"SELECT * FROM positions WHERE game_id IN ({placeholders}) ORDER BY position_id",
        game_ids,
    )
    return _rows_to_dicts(result)


def insert_positions(
    conn: duckdb.DuckDBPyConnection,
    positions: list[Mapping[str, object]],
) -> list[int]:
    """Insert position rows and return new ids."""
    if not positions:
        return []
    row = conn.execute("SELECT MAX(position_id) FROM positions").fetchone()
    next_id = int(row[0] or 0) if row else 0
    ids: list[int] = []
    for pos in positions:
        next_id += 1
        conn.execute(
            """
            INSERT INTO positions (
                position_id,
                game_id,
                user,
                source,
                fen,
                ply,
                move_number,
                side_to_move,
                uci,
                san,
                clock_seconds,
                is_legal
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                next_id,
                pos.get("game_id"),
                pos.get("user"),
                pos.get("source"),
                pos.get("fen"),
                pos.get("ply"),
                pos.get("move_number"),
                pos.get("side_to_move"),
                pos.get("uci"),
                pos.get("san"),
                pos.get("clock_seconds"),
                pos.get("is_legal", True),
            ],
        )
        ids.append(next_id)
    return ids


def insert_tactics(
    conn: duckdb.DuckDBPyConnection,
    rows: list[Mapping[str, object]],
) -> list[int]:
    """Insert tactic rows and return ids."""
    if not rows:
        return []
    row = conn.execute("SELECT MAX(tactic_id) FROM tactics").fetchone()
    next_id = int(row[0] or 0) if row else 0
    ids: list[int] = []
    for tactic in rows:
        next_id += 1
        conn.execute(
            """
            INSERT INTO tactics (
                tactic_id,
                game_id,
                position_id,
                motif,
                severity,
                best_uci,
                best_san,
                explanation,
                eval_cp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                next_id,
                tactic.get("game_id"),
                tactic.get("position_id"),
                tactic.get("motif"),
                tactic.get("severity"),
                tactic.get("best_uci"),
                tactic.get("best_san"),
                tactic.get("explanation"),
                tactic.get("eval_cp"),
            ],
        )
        ids.append(next_id)
    return ids


def insert_tactic_outcomes(
    conn: duckdb.DuckDBPyConnection,
    rows: list[Mapping[str, object]],
) -> list[int]:
    """Insert tactic outcome rows and return ids."""
    if not rows:
        return []
    row = conn.execute("SELECT MAX(outcome_id) FROM tactic_outcomes").fetchone()
    next_id = int(row[0] or 0) if row else 0
    ids: list[int] = []
    for outcome in rows:
        next_id += 1
        conn.execute(
            """
            INSERT INTO tactic_outcomes (
                outcome_id,
                tactic_id,
                result,
                user_uci,
                eval_delta
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                next_id,
                outcome.get("tactic_id"),
                outcome.get("result"),
                outcome.get("user_uci"),
                outcome.get("eval_delta"),
            ],
        )
        ids.append(next_id)
    return ids


def upsert_tactic_with_outcome(
    conn: duckdb.DuckDBPyConnection,
    tactic_row: Mapping[str, object],
    outcome_row: Mapping[str, object],
) -> int:
    """Insert a tactic with its outcome and return the tactic id."""
    BaseDbStore.require_position_id(
        tactic_row,
        "position_id is required when inserting tactics",
    )
    tactic_ids = insert_tactics(conn, [tactic_row])
    tactic_id = tactic_ids[0]
    insert_tactic_outcomes(
        conn,
        [{**outcome_row, "tactic_id": tactic_id}],
    )
    return tactic_id


def delete_game_rows(conn: duckdb.DuckDBPyConnection, game_ids: list[str]) -> None:
    """Delete position, tactic, and outcome rows for the provided games."""
    if not game_ids:
        return
    placeholders = ", ".join(["?"] * len(game_ids))
    tactic_ids = conn.execute(
        f"SELECT tactic_id FROM tactics WHERE game_id IN ({placeholders})",
        game_ids,
    ).fetchall()
    tactic_id_values = [row[0] for row in tactic_ids]
    if tactic_id_values:
        outcome_placeholders = ", ".join(["?"] * len(tactic_id_values))
        conn.execute(
            f"DELETE FROM tactic_outcomes WHERE tactic_id IN ({outcome_placeholders})",
            tactic_id_values,
        )
    conn.execute(
        f"DELETE FROM tactics WHERE game_id IN ({placeholders})",
        game_ids,
    )
    conn.execute(
        f"DELETE FROM positions WHERE game_id IN ({placeholders})",
        game_ids,
    )
    conn.execute(
        f"DELETE FROM raw_pgns WHERE game_id IN ({placeholders})",
        game_ids,
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


def _build_motif_breakdowns(rows: list[dict[str, object]]) -> list[tuple[object, ...]]:
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = (
            row.get("source"),
            row.get("motif"),
            row.get("rating_bucket"),
            row.get("time_control"),
        )
        grouped[key].append(row)
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
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = (
            row.get("source"),
            row.get("motif"),
            row.get("rating_bucket"),
            row.get("time_control"),
        )
        grouped[key].append(row)
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


def fetch_metrics(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    filters: DashboardQuery | None = None,
    **legacy: object,
) -> list[dict[str, object]]:
    """Fetch metrics summary rows with optional filters."""
    resolved = _resolve_dashboard_query(query, filters=filters, **legacy)
    sql = "SELECT * FROM metrics_summary"
    params: list[object] = []
    conditions: list[str] = []
    if resolved.source:
        conditions.append("source = ?")
        params.append(resolved.source)
    _append_optional_filter(conditions, params, "motif = ?", resolved.motif)
    _append_optional_filter(conditions, params, "rating_bucket = ?", resolved.rating_bucket)
    _append_optional_filter(conditions, params, "time_control = ?", resolved.time_control)
    _append_date_range_filters(
        conditions,
        params,
        resolved.start_date,
        resolved.end_date,
        "trend_date",
    )
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    result = conn.execute(sql, params)
    return _rows_to_dicts(result)


def fetch_motif_stats(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    filters: DashboardQuery | None = None,
    **legacy: object,
) -> list[dict[str, object]]:
    """Return motif breakdown metrics."""
    rows = fetch_metrics(conn, query, filters=filters, **legacy)
    return [row for row in rows if row.get("metric_type") == "motif_breakdown"]


def fetch_trend_stats(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    filters: DashboardQuery | None = None,
    **legacy: object,
) -> list[dict[str, object]]:
    """Return trend metrics rows."""
    rows = fetch_metrics(conn, query, filters=filters, **legacy)
    return [row for row in rows if row.get("metric_type") == "trend"]


def write_metrics_version(conn: duckdb.DuckDBPyConnection) -> int:
    """Increment and persist the metrics version."""
    current = fetch_version(conn)
    new_version = current + 1
    conn.execute(
        "INSERT INTO metrics_version (version, updated_at) VALUES (?, CURRENT_TIMESTAMP)",
        [new_version],
    )
    return new_version


def fetch_recent_games(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    limit: int = 20,
    user: str | None = None,
    **legacy: object,
) -> list[dict[str, object]]:
    resolved = _resolve_dashboard_query(query, **legacy)
    final_query, params = _build_recent_games_query(limit, resolved)
    rows = _rows_to_dicts(conn.execute(final_query, params))
    return [_format_recent_game_row(row, user) for row in rows]


def _build_recent_games_query(
    limit: int,
    query: DashboardQuery,
) -> tuple[str, list[object]]:
    normalized_rating = _normalize_filter(query.rating_bucket)
    sql = f"""
        WITH latest_pgns AS (
            {latest_raw_pgns_query()}
        ),
        filtered AS (
            SELECT
                r.game_id,
                r.source,
                r.user,
                r.pgn,
                r.time_control,
                r.user_rating,
                r.last_timestamp_ms
            FROM latest_pgns r
    """
    params: list[object] = []
    conditions: list[str] = []
    _append_time_control_filter(conditions, params, query.time_control, "r.time_control")
    if normalized_rating:
        conditions.append(_rating_bucket_clause(normalized_rating))
    _append_date_range_filters(
        conditions,
        params,
        query.start_date,
        query.end_date,
        "to_timestamp(r.last_timestamp_ms / 1000)",
    )
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += "\n        )\n    "
    if query.source:
        params.append(query.source)
        final_query = (
            sql
            + "SELECT * FROM filtered WHERE source = ? "
            + "ORDER BY last_timestamp_ms DESC, game_id LIMIT ?"
        )
        params.append(limit)
        return final_query, params
    final_query = (
        sql
        + """
        , ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY source
                    ORDER BY last_timestamp_ms DESC
                ) AS source_rank
            FROM filtered
        )
        SELECT * EXCLUDE (source_rank)
        FROM ranked
        WHERE source_rank <= ?
        ORDER BY last_timestamp_ms DESC, game_id
        """
    )
    params.append(limit)
    return final_query, params


def _resolve_opponent_and_color(
    user_lower: str,
    white: object | None,
    black: object | None,
) -> tuple[object | None, str | None]:
    white_lower = _normalize_player_name(white)
    black_lower = _normalize_player_name(black)
    if _is_user_player(white_lower, user_lower):
        return black, "white"
    if _is_user_player(black_lower, user_lower):
        return white, "black"
    return _fallback_opponent(white, black), None


def _normalize_player_name(value: object | None) -> str:
    return str(value or "").lower()


def _is_user_player(player: str, user_lower: str) -> bool:
    return bool(player) and player == user_lower


def _fallback_opponent(white: object | None, black: object | None) -> object | None:
    return black or white


def _timestamp_ms_to_iso(value: object) -> str | None:
    if isinstance(value, (int, float)) and int(value) > 0:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC).isoformat()
    return None


def _resolve_played_at(
    metadata: Mapping[str, object],
    row: Mapping[str, object],
) -> str | None:
    played_at = _timestamp_ms_to_iso(metadata.get("start_timestamp_ms"))
    if played_at:
        return played_at
    return _timestamp_ms_to_iso(row.get("last_timestamp_ms"))


def _format_recent_game_row(row: Mapping[str, object], user: str | None) -> dict[str, object]:
    raw_user = _resolve_recent_game_user(row, user)
    pgn_text = str(row.get("pgn") or "")
    metadata = extract_pgn_metadata(pgn_text, raw_user)
    opponent, user_color = _resolve_opponent_and_color(
        raw_user.lower(),
        metadata.get("white_player"),
        metadata.get("black_player"),
    )
    played_at = _resolve_played_at(metadata, row)
    result = _resolve_recent_game_result(pgn_text, raw_user, metadata.get("result"))
    return _recent_game_payload(
        row,
        {**metadata, "result": result},
        opponent,
        user_color,
        played_at,
    )


def _resolve_recent_game_result(
    pgn_text: str,
    user: str,
    fallback: object,
) -> object:
    """Resolve the result of a recent game from PGN headers."""
    if not pgn_text.strip().startswith("["):
        return fallback
    try:
        headers = chess.pgn.read_headers(StringIO(pgn_text))
        if headers is None:
            return fallback
        return str(_get_game_result_for_user_from_pgn_headers(headers, user))
    except (ValueError, TypeError):
        return fallback


def _resolve_recent_game_user(row: Mapping[str, object], user: str | None) -> str:
    return user or str(row.get("user") or "")


def _recent_game_payload(
    row: Mapping[str, object],
    metadata: Mapping[str, object],
    opponent: object | None,
    user_color: str | None,
    played_at: str | None,
) -> dict[str, object]:
    return {
        "game_id": str(row.get("game_id") or ""),
        "source": row.get("source"),
        "opponent": opponent,
        "result": metadata.get("result"),
        "played_at": played_at,
        "time_control": metadata.get("time_control") or row.get("time_control") or None,
        "user_color": user_color,
    }


def fetch_recent_positions(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    limit: int = 20,
    **legacy: object,
) -> list[dict[str, object]]:
    resolved = _resolve_dashboard_query(query, **legacy)
    normalized_rating = _normalize_filter(resolved.rating_bucket)
    sql = f"""
        WITH latest_pgns AS (
            {latest_raw_pgns_query()}
        )
        SELECT p.*
        FROM positions p
        LEFT JOIN latest_pgns r ON r.game_id = p.game_id AND r.source = p.source
    """
    params: list[object] = []
    conditions: list[str] = []
    if resolved.source:
        conditions.append("p.source = ?")
        params.append(resolved.source)
    _append_time_control_filter(
        conditions,
        params,
        resolved.time_control,
        "r.time_control",
    )
    if normalized_rating:
        conditions.append(_rating_bucket_clause(normalized_rating))
    _append_date_range_filters(
        conditions,
        params,
        resolved.start_date,
        resolved.end_date,
        "p.created_at",
    )
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY p.created_at DESC LIMIT ?"
    params.append(limit)
    result = conn.execute(sql, params)
    return _rows_to_dicts(result)


def fetch_recent_tactics(
    conn: duckdb.DuckDBPyConnection,
    query: DashboardQuery | str | None = None,
    *,
    limit: int = 20,
    **legacy: object,
) -> list[dict[str, object]]:
    resolved = _resolve_dashboard_query(query, **legacy)
    sql, params = _build_recent_tactics_query(limit, resolved)
    return _rows_to_dicts(conn.execute(sql, params))


def _build_recent_tactics_query(
    limit: int,
    query: DashboardQuery,
) -> tuple[str, list[object]]:
    normalized_motif = _normalize_filter(query.motif)
    normalized_rating = _normalize_filter(query.rating_bucket)
    sql = f"""
        WITH latest_pgns AS (
            {latest_raw_pgns_query()}
        )
        SELECT t.*, o.result, o.eval_delta, o.user_uci, p.source
        FROM tactics t
        LEFT JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
        LEFT JOIN positions p ON p.position_id = t.position_id
        LEFT JOIN latest_pgns r ON r.game_id = p.game_id AND r.source = p.source
    """
    params: list[object] = []
    conditions: list[str] = []
    _append_recent_tactics_filters(
        conditions,
        params,
        query,
        normalized_motif,
        normalized_rating,
    )
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY t.created_at DESC LIMIT ?"
    params.append(limit)
    return sql, params


def _append_recent_tactics_filters(
    conditions: list[str],
    params: list[object],
    query: DashboardQuery,
    normalized_motif: str | None,
    normalized_rating: str | None,
) -> None:
    _append_optional_filter(conditions, params, "p.source = ?", query.source)
    _append_optional_filter(conditions, params, "t.motif = ?", normalized_motif)
    _append_time_control_filter(conditions, params, query.time_control, "r.time_control")
    if normalized_rating:
        conditions.append(_rating_bucket_clause(normalized_rating))
    _append_date_range_filters(
        conditions,
        params,
        query.start_date,
        query.end_date,
        "t.created_at",
    )


def _latest_pgns_query() -> str:
    return f"""
        WITH latest_pgns AS (
            {latest_raw_pgns_query()}
        )
        SELECT *
        FROM latest_pgns
        WHERE game_id = ?
    """


def _row_to_dict(
    result: duckdb.DuckDBPyConnection | duckdb.DuckDBPyRelation,
    row: tuple[object, ...],
) -> dict[str, object]:
    columns = [desc[0] for desc in result.description]
    return dict(zip(columns, row, strict=True))


def _fetch_latest_pgn_row(
    conn: duckdb.DuckDBPyConnection,
    game_id: str,
    source: str | None,
) -> tuple[tuple[object, ...] | None, duckdb.DuckDBPyConnection]:
    query = _latest_pgns_query()
    params: list[object] = [game_id]
    if source:
        query += " AND source = ?"
        params.append(source)
    result = conn.execute(query, params)
    row = result.fetchone()
    if row or not source:
        return row, result
    fallback_result = conn.execute(_latest_pgns_query(), [game_id])
    return fallback_result.fetchone(), fallback_result


def _fetch_game_analysis_rows(
    conn: duckdb.DuckDBPyConnection,
    game_id: str,
    source: str | None,
) -> list[dict[str, object]]:
    analysis_query = f"""
        SELECT
            {TACTIC_ANALYSIS_COLUMNS},
            {OUTCOME_COLUMNS},
            p.move_number,
            p.ply,
            p.san,
            p.uci,
            p.side_to_move,
            p.fen
        FROM tactics t
        LEFT JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
        LEFT JOIN positions p ON p.position_id = t.position_id
        WHERE t.game_id = ?
    """
    analysis_params: list[object] = [game_id]
    if source:
        analysis_query += " AND p.source = ?"
        analysis_params.append(source)
    analysis_query += " ORDER BY p.ply ASC, t.created_at ASC"
    return _rows_to_dicts(conn.execute(analysis_query, analysis_params))


def fetch_game_detail(
    conn: duckdb.DuckDBPyConnection,
    game_id: str,
    user: str,
    source: str | None = None,
) -> dict[str, object]:
    """Fetch a detailed game payload including analysis rows."""
    row, result = _fetch_latest_pgn_row(conn, game_id, source)
    if not row:
        return {
            "game_id": game_id,
            "source": source,
            "pgn": None,
            "metadata": {},
            "analysis": [],
        }
    pgn_row = _row_to_dict(result, row)
    pgn_value = pgn_row.get("pgn")
    pgn = str(pgn_value) if pgn_value is not None else None
    metadata = extract_pgn_metadata(pgn or "", user)
    analysis_rows = _fetch_game_analysis_rows(conn, game_id, source)
    return {
        "game_id": game_id,
        "source": pgn_row.get("source") or source,
        "pgn": pgn,
        "metadata": metadata,
        "analysis": analysis_rows,
    }


def fetch_practice_tactic(
    conn: duckdb.DuckDBPyConnection, tactic_id: int
) -> dict[str, object] | None:
    """Fetch a single tactic for practice flows."""
    result = conn.execute(
        f"""
        SELECT
            {TACTIC_COLUMNS},
            {OUTCOME_COLUMNS},
            p.source,
            p.fen,
            p.uci AS position_uci,
            p.san,
            p.ply,
            p.move_number,
            p.side_to_move,
            p.clock_seconds
        FROM tactics t
        LEFT JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
        LEFT JOIN positions p ON p.position_id = t.position_id
        WHERE t.tactic_id = ?
        """,
        [tactic_id],
    )
    rows = _rows_to_dicts(result)
    return rows[0] if rows else None


def _require_practice_tactic(
    conn: duckdb.DuckDBPyConnection,
    tactic_id: int,
    position_id: int,
) -> dict[str, object]:
    """Return the tactic for a position or raise a ValueError."""
    tactic = fetch_practice_tactic(conn, tactic_id)
    if not tactic or tactic.get("position_id") != position_id:
        raise ValueError("Tactic not found for position")
    return tactic


def _normalize_attempted_uci(attempted_uci: str) -> str:
    """Normalize and validate an attempted UCI move."""
    trimmed = attempted_uci.strip()
    if not trimmed:
        raise ValueError("attempted_uci is required")
    return trimmed


def _normalize_best_uci(tactic: Mapping[str, object]) -> str:
    """Return the normalized best UCI move for a tactic."""
    best_uci_raw = tactic.get("best_uci")
    return str(best_uci_raw).strip() if best_uci_raw is not None else ""


def _resolve_practice_explanation(
    tactic: Mapping[str, object],
    best_uci: str,
) -> tuple[str | None, str | None]:
    """Resolve explanation fields for practice payloads."""
    fen = _string_or_none(tactic.get("fen"))
    motif = _string_or_none(tactic.get("motif"))
    best_san = _string_or_none(tactic.get("best_san"))
    explanation = _string_or_none(tactic.get("explanation"))
    generated_san, generated_explanation = format_tactic_explanation(fen, best_uci, motif)
    return _resolve_explanation(best_san, explanation, generated_san, generated_explanation)


def _string_or_none(value: object) -> str | None:
    """Return a stripped string or None for empty values."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_explanation(
    best_san: str | None,
    explanation: str | None,
    generated_san: str | None,
    generated_explanation: str | None,
) -> tuple[str | None, str | None]:
    """Pick the best available SAN and explanation strings."""
    if not best_san:
        best_san = generated_san or None
    if not explanation:
        explanation = generated_explanation or None
    return best_san, explanation


@dataclass(frozen=True)
class PracticeAttemptInputs:
    """Grouped inputs for practice attempt payloads."""

    tactic: Mapping[str, object]
    tactic_id: int
    position_id: int
    attempted_uci: str
    best_uci: str
    correct: bool
    latency_ms: int | None


def _build_practice_attempt_payload(
    inputs: PracticeAttemptInputs,
) -> dict[str, object]:
    """Build the practice attempt payload for persistence."""
    return {
        "tactic_id": inputs.tactic_id,
        "position_id": inputs.position_id,
        "source": inputs.tactic.get("source"),
        "attempted_uci": inputs.attempted_uci,
        "correct": inputs.correct,
        "success": inputs.correct,
        "best_uci": inputs.best_uci,
        "motif": inputs.tactic.get("motif", "unknown"),
        "severity": inputs.tactic.get("severity", 0.0),
        "eval_delta": inputs.tactic.get("eval_delta", 0) or 0,
        "latency_ms": inputs.latency_ms,
    }


def _build_practice_message(
    correct: bool,
    tactic: Mapping[str, object],
    best_uci: str,
) -> str:
    """Return the user-facing practice message."""
    if correct:
        return f"Correct! {tactic.get('motif', 'tactic')} found."
    return f"Missed it. Best move was {best_uci or '--'}."


def grade_practice_attempt(
    conn: duckdb.DuckDBPyConnection,
    tactic_id: int,
    position_id: int,
    attempted_uci: str,
    latency_ms: int | None = None,
) -> dict[str, object]:
    """Grade a practice attempt and persist the result."""
    tactic = _require_practice_tactic(conn, tactic_id, position_id)
    trimmed_attempt = _normalize_attempted_uci(attempted_uci)
    best_uci = _normalize_best_uci(tactic)
    correct = bool(best_uci) and trimmed_attempt.lower() == best_uci.lower()
    best_san, explanation = _resolve_practice_explanation(tactic, best_uci)
    attempt_payload = _build_practice_attempt_payload(
        PracticeAttemptInputs(
            tactic=tactic,
            tactic_id=tactic_id,
            position_id=position_id,
            attempted_uci=trimmed_attempt,
            best_uci=best_uci,
            correct=correct,
            latency_ms=latency_ms,
        )
    )
    attempt_id = record_training_attempt(conn, attempt_payload)
    message = _build_practice_message(correct, tactic, best_uci)
    return {
        "attempt_id": attempt_id,
        "tactic_id": tactic_id,
        "position_id": position_id,
        "source": tactic.get("source"),
        "attempted_uci": trimmed_attempt,
        "best_uci": best_uci,
        "correct": correct,
        "success": correct,
        "motif": tactic.get("motif", "unknown"),
        "severity": tactic.get("severity", 0.0),
        "eval_delta": tactic.get("eval_delta", 0) or 0,
        "message": message,
        "best_san": best_san,
        "explanation": explanation,
        "latency_ms": latency_ms,
    }


def fetch_practice_queue(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 20,
    source: str | None = None,
    include_failed_attempt: bool = False,
    exclude_seen: bool = False,
) -> list[dict[str, object]]:
    """Return a queue of practice tactics."""
    results = ["missed"]
    if include_failed_attempt:
        results.append("failed_attempt")
    placeholders = ", ".join(["?"] * len(results))
    query = f"""
        SELECT
            {TACTIC_QUEUE_COLUMNS},
            {OUTCOME_COLUMNS},
            p.source,
            p.fen,
            p.uci AS position_uci,
            p.san,
            p.ply,
            p.move_number,
            p.side_to_move,
            p.clock_seconds
        FROM tactics t
        INNER JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
        INNER JOIN positions p ON p.position_id = t.position_id
        WHERE o.result IN ({placeholders})
    """
    params: list[object] = list(results)
    if source:
        query += " AND p.source = ?"
        params.append(source)
    if exclude_seen:
        query += " AND t.tactic_id NOT IN (SELECT tactic_id FROM training_attempts"
        if source:
            query += " WHERE source = ?"
            params.append(source)
        query += ")"
    query += " ORDER BY t.created_at DESC LIMIT ?"
    params.append(limit)
    result = conn.execute(query, params)
    return _rows_to_dicts(result)


def fetch_version(conn: duckdb.DuckDBPyConnection) -> int:
    """Fetch the latest metrics version."""
    version_row = conn.execute("SELECT MAX(version) FROM metrics_version").fetchone()
    if not version_row or version_row[0] is None:
        return 0
    return int(version_row[0])


_VULTURE_USED = (SCHEMA_VERSION, _ensure_column, _coerce_metric_count)
