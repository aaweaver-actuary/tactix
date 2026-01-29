from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Iterable, List, Mapping

import duckdb
from tactix.base_db_store import BaseDbStore, BaseDbStoreContext
from tactix.logging_utils import get_logger
from tactix.tactics_explanation import format_tactic_explanation

logger = get_logger(__name__)


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

SCHEMA_VERSION = 6


class DuckDbStore(BaseDbStore):
    """DuckDB-backed store implementation."""

    def __init__(
        self, context: BaseDbStoreContext, db_path: Path | None = None
    ) -> None:
        super().__init__(context)
        self._db_path = db_path or context.settings.duckdb_path

    @property
    def db_path(self) -> Path:
        return self._db_path

    def get_dashboard_payload(
        self,
        source: str | None = None,
        motif: str | None = None,
        rating_bucket: str | None = None,
        time_control: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, object]:
        conn = get_connection(self._db_path)
        init_schema(conn)
        active_source = None if source in (None, "all") else source
        response_source = "all" if active_source is None else active_source
        return {
            "source": response_source,
            "user": self.settings.user,
            "metrics": fetch_metrics(
                conn,
                source=active_source,
                motif=motif,
                rating_bucket=rating_bucket,
                time_control=time_control,
                start_date=start_date,
                end_date=end_date,
            ),
            "recent_games": fetch_recent_games(
                conn,
                source=active_source,
                rating_bucket=rating_bucket,
                time_control=time_control,
                start_date=start_date,
                end_date=end_date,
                user=self.settings.user,
            ),
            "positions": fetch_recent_positions(
                conn,
                source=active_source,
                rating_bucket=rating_bucket,
                time_control=time_control,
                start_date=start_date,
                end_date=end_date,
            ),
            "tactics": fetch_recent_tactics(
                conn,
                source=active_source,
                motif=motif,
                rating_bucket=rating_bucket,
                time_control=time_control,
                start_date=start_date,
                end_date=end_date,
            ),
            "metrics_version": fetch_version(conn),
        }


def get_connection(db_path: Path) -> duckdb.DuckDBPyConnection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Opening DuckDB at %s", db_path)
    try:
        return duckdb.connect(str(db_path))
    except duckdb.InternalException as exc:
        if not _should_attempt_wal_recovery(exc):
            raise
        wal_path = db_path.with_name(f"{db_path.name}.wal")
        if not wal_path.exists():
            raise
        logger.warning("Removing DuckDB WAL after replay error: %s", wal_path)
        try:
            wal_path.unlink()
        except OSError:
            logger.exception("Failed to remove WAL file: %s", wal_path)
            raise
        return duckdb.connect(str(db_path))


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    migrate_schema(conn)
    count_row = conn.execute("SELECT COUNT(*) FROM metrics_version").fetchone()
    count = int(count_row[0]) if count_row else 0
    if count == 0:
        conn.execute("INSERT INTO metrics_version VALUES (0, CURRENT_TIMESTAMP)")


def migrate_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(SCHEMA_VERSION_SCHEMA)
    current_version = _get_schema_version(conn)
    max_target_version = SCHEMA_VERSION
    if current_version == 0 and _is_legacy_raw_pgns(conn):
        # Legacy databases created before training_attempt latency tracking
        # should remain at v3 unless explicitly upgraded.
        max_target_version = 3
    for target_version, migration in _SCHEMA_MIGRATIONS:
        if target_version > max_target_version or current_version >= target_version:
            continue
        logger.info("Applying DuckDB schema migration v%s", target_version)
        migration(conn)
        _set_schema_version(conn, target_version)
        current_version = target_version


def _should_attempt_wal_recovery(exc: Exception) -> bool:
    message = str(exc).lower()
    if "wal" not in message:
        return False
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    env = os.getenv("TACTIX_ENV", "").lower()
    if env in {"test", "dev"}:
        return True
    allow = os.getenv("TACTIX_ALLOW_WAL_RECOVERY", "").lower()
    return allow in {"1", "true", "yes"}


def _is_legacy_raw_pgns(conn: duckdb.DuckDBPyConnection) -> bool:
    try:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info('raw_pgns')").fetchall()
        }
    except Exception:
        return False
    return bool(columns) and "raw_pgn_id" not in columns


def get_schema_version(conn: duckdb.DuckDBPyConnection) -> int:
    return _get_schema_version(conn)


def _get_schema_version(conn: duckdb.DuckDBPyConnection) -> int:
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if not row:
        return 0
    return int(row[0] or 0)


def _set_schema_version(conn: duckdb.DuckDBPyConnection, version: int) -> None:
    conn.execute("DELETE FROM schema_version")
    conn.execute("INSERT INTO schema_version VALUES (?, CURRENT_TIMESTAMP)", [version])


def _migration_base_tables(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(RAW_PGNS_SCHEMA)
    conn.execute(POSITIONS_SCHEMA)
    conn.execute(TACTICS_SCHEMA)
    conn.execute(TACTIC_OUTCOMES_SCHEMA)
    conn.execute(METRICS_VERSION_SCHEMA)
    conn.execute(METRICS_SUMMARY_SCHEMA)
    conn.execute(TRAINING_ATTEMPTS_SCHEMA)


def _migration_raw_pgns_versioning(conn: duckdb.DuckDBPyConnection) -> None:
    _ensure_raw_pgns_versioned(conn)


def _migration_add_columns(conn: duckdb.DuckDBPyConnection) -> None:
    _ensure_column(conn, "positions", "side_to_move", "TEXT")
    _ensure_column(conn, "metrics_summary", "source", "TEXT")
    _ensure_column(conn, "metrics_summary", "metric_type", "TEXT")
    _ensure_column(conn, "metrics_summary", "window_days", "INTEGER")
    _ensure_column(conn, "metrics_summary", "trend_date", "DATE")
    _ensure_column(conn, "metrics_summary", "rating_bucket", "TEXT")
    _ensure_column(conn, "metrics_summary", "time_control", "TEXT")
    _ensure_column(conn, "metrics_summary", "found_rate", "DOUBLE")
    _ensure_column(conn, "metrics_summary", "miss_rate", "DOUBLE")
    _ensure_column(conn, "training_attempts", "source", "TEXT")
    _ensure_column(conn, "training_attempts", "attempted_uci", "TEXT")
    _ensure_column(conn, "training_attempts", "correct", "BOOLEAN")
    _ensure_column(conn, "training_attempts", "best_uci", "TEXT")
    _ensure_column(conn, "training_attempts", "motif", "TEXT")
    _ensure_column(conn, "training_attempts", "severity", "DOUBLE")
    _ensure_column(conn, "training_attempts", "eval_delta", "INTEGER")


def _migration_add_training_attempt_latency(conn: duckdb.DuckDBPyConnection) -> None:
    _ensure_column(conn, "training_attempts", "success", "BOOLEAN")
    _ensure_column(conn, "training_attempts", "latency_ms", "BIGINT")


def _migration_add_position_legality(conn: duckdb.DuckDBPyConnection) -> None:
    _ensure_column(conn, "positions", "is_legal", "BOOLEAN")


def _migration_add_tactic_explanations(conn: duckdb.DuckDBPyConnection) -> None:
    _ensure_column(conn, "tactics", "best_san", "TEXT")
    _ensure_column(conn, "tactics", "explanation", "TEXT")


_SCHEMA_MIGRATIONS = [
    (1, _migration_base_tables),
    (2, _migration_raw_pgns_versioning),
    (3, _migration_add_columns),
    (4, _migration_add_training_attempt_latency),
    (5, _migration_add_position_legality),
    (6, _migration_add_tactic_explanations),
]


def hash_pgn(pgn: str) -> str:
    return BaseDbStore.hash_pgn_text(pgn)


def _ensure_raw_pgns_versioned(conn: duckdb.DuckDBPyConnection) -> None:
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info('raw_pgns')").fetchall()
    }
    if "raw_pgn_id" not in columns:
        conn.execute("BEGIN TRANSACTION")
        try:
            existing_tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
            if "raw_pgns_legacy" in existing_tables:
                conn.execute("DROP TABLE raw_pgns_legacy")
            conn.execute("ALTER TABLE raw_pgns RENAME TO raw_pgns_legacy")
            conn.execute(RAW_PGNS_SCHEMA)
            legacy_rows = conn.execute(
                "SELECT game_id, user, source, fetched_at, pgn, last_timestamp_ms, cursor FROM raw_pgns_legacy"
            ).fetchall()
            next_id = 0
            inserts = []
            for row in legacy_rows:
                next_id += 1
                pgn_text = row[4] or ""
                metadata = BaseDbStore.extract_pgn_metadata(pgn_text, str(row[1]))
                inserts.append(
                    (
                        next_id,
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        pgn_text,
                        hash_pgn(pgn_text),
                        1,
                        metadata.get("user_rating"),
                        metadata.get("time_control"),
                        datetime.now(timezone.utc),
                        row[5],
                        row[6],
                    )
                )
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
        except Exception:  # noqa: BLE001
            conn.execute("ROLLBACK")
            raise
    else:
        _ensure_column(conn, "raw_pgns", "pgn_hash", "TEXT")
        _ensure_column(conn, "raw_pgns", "pgn_version", "INTEGER")
        _ensure_column(conn, "raw_pgns", "user_rating", "INTEGER")
        _ensure_column(conn, "raw_pgns", "time_control", "TEXT")
        _ensure_column(conn, "raw_pgns", "ingested_at", "TIMESTAMP")
        _ensure_column(conn, "raw_pgns", "cursor", "TEXT")


def _ensure_column(
    conn: duckdb.DuckDBPyConnection, table: str, column: str, definition: str
) -> None:
    columns = {
        row[1] for row in conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    }
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def upsert_raw_pgns(
    conn: duckdb.DuckDBPyConnection,
    rows: Iterable[Mapping[str, object]],
) -> int:
    rows_list = list(rows)
    if not rows_list:
        return 0
    conn.execute("BEGIN TRANSACTION")
    try:
        next_row = conn.execute(
            "SELECT COALESCE(MAX(raw_pgn_id), 0) FROM raw_pgns"
        ).fetchone()
        next_id = int(next_row[0]) if next_row else 0
        latest_cache: dict[tuple[str, str], tuple[str | None, int]] = {}
        inserted = 0
        for row in rows_list:
            game_id = str(row["game_id"])
            source = str(row["source"])
            pgn_text = str(row["pgn"])
            metadata = BaseDbStore.extract_pgn_metadata(pgn_text, str(row["user"]))
            pgn_hash = hash_pgn(pgn_text)
            key = (game_id, source)
            if key in latest_cache:
                latest_hash, latest_version = latest_cache[key]
            else:
                existing = conn.execute(
                    """
                    SELECT pgn_hash, pgn_version
                    FROM raw_pgns
                    WHERE game_id = ? AND source = ?
                    ORDER BY pgn_version DESC
                    LIMIT 1
                    """,
                    [game_id, source],
                ).fetchone()
                if existing:
                    latest_hash, latest_version = existing[0], int(existing[1] or 0)
                else:
                    latest_hash, latest_version = None, 0
            if latest_hash == pgn_hash:
                latest_cache[key] = (latest_hash, latest_version)
                continue
            next_id += 1
            new_version = latest_version + 1
            conn.execute(
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
                (
                    next_id,
                    game_id,
                    row["user"],
                    source,
                    row.get("fetched_at", datetime.now(timezone.utc)),
                    pgn_text,
                    pgn_hash,
                    new_version,
                    metadata.get("user_rating"),
                    metadata.get("time_control"),
                    datetime.now(timezone.utc),
                    row.get("last_timestamp_ms", 0),
                    row.get("cursor"),
                ),
            )
            latest_cache[key] = (pgn_hash, new_version)
            inserted += 1
        conn.execute("COMMIT")
    except Exception:  # noqa: BLE001
        conn.execute("ROLLBACK")
        raise
    return inserted


def fetch_latest_pgn_hashes(
    conn: duckdb.DuckDBPyConnection,
    game_ids: list[str],
    source: str,
) -> dict[str, str]:
    if not game_ids:
        return {}
    placeholders = ", ".join(["?"] * len(game_ids))
    params: list[object] = [source, *game_ids, source]
    rows = conn.execute(
        f"""
        SELECT raw.game_id, raw.pgn_hash
        FROM raw_pgns AS raw
        JOIN (
            SELECT game_id, MAX(pgn_version) AS max_version
            FROM raw_pgns
            WHERE source = ? AND game_id IN ({placeholders})
            GROUP BY game_id
        ) AS latest
        ON raw.game_id = latest.game_id AND raw.pgn_version = latest.max_version
        WHERE raw.source = ?
        """,
        params,
    ).fetchall()
    return {str(row[0]): str(row[1]) for row in rows if row[0] is not None}


def fetch_latest_raw_pgns(
    conn: duckdb.DuckDBPyConnection,
    source: str | None = None,
    limit: int | None = None,
) -> list[dict[str, object]]:
    params: list[object] = []
    filters = []
    if source:
        filters.append("source = ?")
        params.append(source)
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    limit_clause = ""
    if limit is not None:
        limit_clause = "LIMIT ?"
        params.append(int(limit))
    result = conn.execute(
        f"""
        SELECT * EXCLUDE (rn)
        FROM (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY game_id, source
                    ORDER BY pgn_version DESC
                ) AS rn
            FROM raw_pgns
            {where_clause}
        )
        WHERE rn = 1
        ORDER BY last_timestamp_ms DESC, game_id
        {limit_clause}
        """,
        params,
    )
    return _rows_to_dicts(result)


def fetch_raw_pgns_summary(
    conn: duckdb.DuckDBPyConnection,
    source: str | None = None,
) -> list[dict[str, object]]:
    params: list[object] = []
    where_clause = ""
    if source:
        where_clause = "WHERE source = ?"
        params.append(source)
    result = conn.execute(
        f"""
        SELECT
            source,
            COUNT(*) AS total,
            SUM(CASE WHEN pgn_hash IS NOT NULL AND pgn_hash <> '' THEN 1 ELSE 0 END) AS hashed,
            SUM(CASE WHEN pgn_hash IS NULL OR pgn_hash = '' THEN 1 ELSE 0 END) AS missing
        FROM raw_pgns
        {where_clause}
        GROUP BY source
        """,
        params,
    )
    return _rows_to_dicts(result)


def fetch_position_counts(
    conn: duckdb.DuckDBPyConnection,
    game_ids: list[str],
    source: str,
) -> dict[str, int]:
    if not game_ids:
        return {}
    placeholders = ", ".join(["?"] * len(game_ids))
    params: list[object] = [*game_ids, source]
    rows = conn.execute(
        f"""
        SELECT game_id, COUNT(*)
        FROM positions
        WHERE game_id IN ({placeholders}) AND source = ?
        GROUP BY game_id
        """,
        params,
    ).fetchall()
    return {str(row[0]): int(row[1]) for row in rows if row[0] is not None}


def delete_game_rows(conn: duckdb.DuckDBPyConnection, game_ids: list[str]) -> None:
    if not game_ids:
        return
    conn.execute("BEGIN TRANSACTION")
    try:
        for game_id in game_ids:
            conn.execute(
                "DELETE FROM tactic_outcomes WHERE tactic_id IN (SELECT tactic_id FROM tactics WHERE game_id = ?)",
                [game_id],
            )
            conn.execute("DELETE FROM tactics WHERE game_id = ?", [game_id])
            conn.execute("DELETE FROM positions WHERE game_id = ?", [game_id])
        conn.execute("COMMIT")
    except Exception:  # noqa: BLE001
        conn.execute("ROLLBACK")
        raise


def insert_positions(
    conn: duckdb.DuckDBPyConnection,
    rows: Iterable[Mapping[str, object]],
) -> List[int]:
    rows_list = list(rows)
    if not rows_list:
        return []
    start_row = conn.execute(
        "SELECT COALESCE(MAX(position_id), 0) FROM positions"
    ).fetchone()
    start_id = int(start_row[0]) if start_row else 0
    conn.execute("BEGIN TRANSACTION")
    position_ids: List[int] = []
    try:
        for idx, row in enumerate(rows_list, start=1):
            position_id = start_id + idx
            conn.execute(
                """
                INSERT INTO positions (position_id, game_id, user, source, fen, ply, move_number, side_to_move, uci, san, clock_seconds, is_legal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position_id,
                    row["game_id"],
                    row["user"],
                    row["source"],
                    row["fen"],
                    row["ply"],
                    row["move_number"],
                    row.get("side_to_move"),
                    row["uci"],
                    row.get("san", ""),
                    row.get("clock_seconds"),
                    row.get("is_legal", True),
                ),
            )
            position_ids.append(position_id)
        conn.execute("COMMIT")
    except Exception:  # noqa: BLE001
        conn.execute("ROLLBACK")
        raise
    return position_ids


def fetch_positions_for_games(
    conn: duckdb.DuckDBPyConnection, game_ids: list[str]
) -> list[dict[str, object]]:
    if not game_ids:
        return []
    placeholders = ", ".join(["?"] * len(game_ids))
    result = conn.execute(
        f"SELECT * FROM positions WHERE game_id IN ({placeholders}) ORDER BY position_id",
        game_ids,
    )
    return _rows_to_dicts(result)


def fetch_unanalyzed_positions(
    conn: duckdb.DuckDBPyConnection,
    game_ids: list[str] | None = None,
    source: str | None = None,
    limit: int | None = None,
) -> list[dict[str, object]]:
    params: list[object] = []
    filters: list[str] = ["t.position_id IS NULL"]
    if game_ids:
        placeholders = ", ".join(["?"] * len(game_ids))
        filters.append(f"p.game_id IN ({placeholders})")
        params.extend(game_ids)
    if source:
        filters.append("p.source = ?")
        params.append(source)
    where_clause = f"WHERE {' AND '.join(filters)}"
    limit_clause = ""
    if limit is not None:
        limit_clause = "LIMIT ?"
        params.append(int(limit))
    result = conn.execute(
        f"""
        SELECT p.*
        FROM positions AS p
        LEFT JOIN tactics AS t
            ON p.position_id = t.position_id
        {where_clause}
        ORDER BY p.position_id
        {limit_clause}
        """,
        params,
    )
    return _rows_to_dicts(result)


def insert_tactics(
    conn: duckdb.DuckDBPyConnection,
    rows: Iterable[Mapping[str, object]],
) -> List[int]:
    rows_list = list(rows)
    if not rows_list:
        return []
    start_row = conn.execute(
        "SELECT COALESCE(MAX(tactic_id), 0) FROM tactics"
    ).fetchone()
    start_id = int(start_row[0]) if start_row else 0
    conn.execute("BEGIN TRANSACTION")
    tactic_ids: List[int] = []
    try:
        for idx, row in enumerate(rows_list, start=1):
            tactic_id = start_id + idx
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
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tactic_id,
                    row["game_id"],
                    row["position_id"],
                    row.get("motif", "unknown"),
                    row.get("severity", 0.0),
                    row.get("best_uci", ""),
                    row.get("best_san"),
                    row.get("explanation"),
                    row.get("eval_cp", 0),
                ),
            )
            tactic_ids.append(tactic_id)
        conn.execute("COMMIT")
    except Exception:  # noqa: BLE001
        conn.execute("ROLLBACK")
        raise
    return tactic_ids


def insert_tactic_outcomes(
    conn: duckdb.DuckDBPyConnection,
    rows: Iterable[Mapping[str, object]],
) -> None:
    rows_list = list(rows)
    if not rows_list:
        return
    start_row = conn.execute(
        "SELECT COALESCE(MAX(outcome_id), 0) FROM tactic_outcomes"
    ).fetchone()
    start_id = int(start_row[0]) if start_row else 0
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.executemany(
            """
            INSERT INTO tactic_outcomes (outcome_id, tactic_id, result, user_uci, eval_delta)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    start_id + idx,
                    row["tactic_id"],
                    row.get("result", "unclear"),
                    row.get("user_uci", ""),
                    row.get("eval_delta", 0),
                )
                for idx, row in enumerate(rows_list, start=1)
            ],
        )
        conn.execute("COMMIT")
    except Exception:  # noqa: BLE001
        conn.execute("ROLLBACK")
        raise


def record_training_attempt(
    conn: duckdb.DuckDBPyConnection,
    attempt: Mapping[str, object],
) -> int:
    conn.execute("BEGIN TRANSACTION")
    try:
        attempt_row = conn.execute(
            "SELECT COALESCE(MAX(attempt_id), 0) FROM training_attempts"
        ).fetchone()
        attempt_id = (int(attempt_row[0]) if attempt_row else 0) + 1
        conn.execute(
            """
            INSERT INTO training_attempts (
                attempt_id,
                tactic_id,
                position_id,
                source,
                attempted_uci,
                correct,
                success,
                best_uci,
                motif,
                severity,
                eval_delta,
                latency_ms
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                attempt["tactic_id"],
                attempt["position_id"],
                attempt.get("source"),
                attempt.get("attempted_uci", ""),
                bool(attempt.get("correct", False)),
                bool(attempt.get("success", attempt.get("correct", False))),
                attempt.get("best_uci", ""),
                attempt.get("motif", "unknown"),
                attempt.get("severity", 0.0),
                attempt.get("eval_delta", 0),
                attempt.get("latency_ms"),
            ),
        )
        conn.execute("COMMIT")
    except Exception:  # noqa: BLE001
        conn.execute("ROLLBACK")
        raise
    return attempt_id


def upsert_tactic_with_outcome(
    conn: duckdb.DuckDBPyConnection,
    tactic_row: Mapping[str, object],
    outcome_row: Mapping[str, object],
) -> int:
    position_id = tactic_row.get("position_id")
    if position_id is None:
        raise ValueError("position_id is required for tactic upsert")
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute(
            "DELETE FROM tactic_outcomes WHERE tactic_id IN (SELECT tactic_id FROM tactics WHERE position_id = ?)",
            [position_id],
        )
        conn.execute("DELETE FROM tactics WHERE position_id = ?", [position_id])

        tactic_row_id = conn.execute(
            "SELECT COALESCE(MAX(tactic_id), 0) FROM tactics"
        ).fetchone()
        tactic_id = (int(tactic_row_id[0]) if tactic_row_id else 0) + 1
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
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tactic_id,
                tactic_row["game_id"],
                position_id,
                tactic_row.get("motif", "unknown"),
                tactic_row.get("severity", 0.0),
                tactic_row.get("best_uci", ""),
                tactic_row.get("best_san"),
                tactic_row.get("explanation"),
                tactic_row.get("eval_cp", 0),
            ),
        )
        outcome_row_id = conn.execute(
            "SELECT COALESCE(MAX(outcome_id), 0) FROM tactic_outcomes"
        ).fetchone()
        outcome_id = (int(outcome_row_id[0]) if outcome_row_id else 0) + 1
        conn.execute(
            """
            INSERT INTO tactic_outcomes (outcome_id, tactic_id, result, user_uci, eval_delta)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                outcome_id,
                tactic_id,
                outcome_row.get("result", "unclear"),
                outcome_row.get("user_uci", ""),
                outcome_row.get("eval_delta", 0),
            ),
        )
        conn.execute("COMMIT")
    except Exception:  # noqa: BLE001
        conn.execute("ROLLBACK")
        raise
    return tactic_id


def write_metrics_version(conn: duckdb.DuckDBPyConnection) -> int:
    conn.execute(
        "UPDATE metrics_version SET version = version + 1, updated_at = CURRENT_TIMESTAMP"
    )
    version_row = conn.execute("SELECT version FROM metrics_version").fetchone()
    return int(version_row[0]) if version_row else 0


def update_metrics_summary(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("DELETE FROM metrics_summary")
    conn.execute(
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
        )
        WITH latest_pgns AS (
            SELECT * EXCLUDE (rn)
            FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY game_id, source
                        ORDER BY pgn_version DESC
                    ) AS rn
                FROM raw_pgns
            )
            WHERE rn = 1
        ),
        tactic_events AS (
            SELECT
                COALESCE(p.source, 'unknown') AS source,
                t.motif AS motif,
                COALESCE(o.result, 'unclear') AS result,
                COALESCE(
                    r.time_control,
                    NULLIF(
                        regexp_extract(r.pgn, '\\[TimeControl "([^\\"]+)"\\]', 1),
                        ''
                    ),
                    'unknown'
                ) AS time_control,
                p.clock_seconds AS clock_seconds,
                CASE
                    WHEN r.user_rating IS NULL THEN 'unknown'
                    WHEN r.user_rating < 1200 THEN '<1200'
                    WHEN r.user_rating < 1400 THEN '1200-1399'
                    WHEN r.user_rating < 1600 THEN '1400-1599'
                    WHEN r.user_rating < 1800 THEN '1600-1799'
                    ELSE '1800+'
                END AS rating_bucket,
                p.game_id AS game_id,
                r.last_timestamp_ms AS last_timestamp_ms,
                CAST(date_trunc('day', to_timestamp(r.last_timestamp_ms / 1000)) AS DATE) AS trend_date
            FROM tactics t
            LEFT JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
            LEFT JOIN positions p ON p.position_id = t.position_id
            LEFT JOIN latest_pgns r ON r.game_id = p.game_id AND r.source = p.source
        ),
        breakdown AS (
            SELECT
                source,
                'motif_breakdown' AS metric_type,
                motif,
                NULL::INTEGER AS window_days,
                NULL::DATE AS trend_date,
                'all' AS rating_bucket,
                'all' AS time_control,
                COUNT(*) AS total,
                SUM(CASE WHEN result = 'found' THEN 1 ELSE 0 END) AS found,
                SUM(CASE WHEN result = 'missed' THEN 1 ELSE 0 END) AS missed,
                SUM(CASE WHEN result = 'failed_attempt' THEN 1 ELSE 0 END) AS failed_attempt,
                SUM(CASE WHEN result = 'unclear' THEN 1 ELSE 0 END) AS unclear
            FROM tactic_events
            GROUP BY source, motif
        ),
        breakdown_split AS (
            SELECT
                source,
                'motif_breakdown' AS metric_type,
                motif,
                NULL::INTEGER AS window_days,
                NULL::DATE AS trend_date,
                rating_bucket,
                time_control,
                COUNT(*) AS total,
                SUM(CASE WHEN result = 'found' THEN 1 ELSE 0 END) AS found,
                SUM(CASE WHEN result = 'missed' THEN 1 ELSE 0 END) AS missed,
                SUM(CASE WHEN result = 'failed_attempt' THEN 1 ELSE 0 END) AS failed_attempt,
                SUM(CASE WHEN result = 'unclear' THEN 1 ELSE 0 END) AS unclear
            FROM tactic_events
            GROUP BY source, motif, rating_bucket, time_control
        ),
        per_game AS (
            SELECT
                source,
                motif,
                rating_bucket,
                time_control,
                game_id,
                MAX(last_timestamp_ms) AS last_timestamp_ms,
                MAX(trend_date) AS trend_date,
                COUNT(*) AS total,
                SUM(CASE WHEN result = 'found' THEN 1 ELSE 0 END) AS found,
                SUM(CASE WHEN result = 'missed' THEN 1 ELSE 0 END) AS missed,
                SUM(CASE WHEN result = 'failed_attempt' THEN 1 ELSE 0 END) AS failed_attempt,
                SUM(CASE WHEN result = 'unclear' THEN 1 ELSE 0 END) AS unclear
            FROM tactic_events
            WHERE last_timestamp_ms IS NOT NULL
            GROUP BY source, motif, rating_bucket, time_control, game_id
        ),
        rolling AS (
            SELECT
                *,
                AVG(found::DOUBLE / NULLIF(total, 0)) OVER (
                    PARTITION BY source, motif, rating_bucket, time_control
                    ORDER BY last_timestamp_ms
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                ) AS found_rate_7,
                AVG(missed::DOUBLE / NULLIF(total, 0)) OVER (
                    PARTITION BY source, motif, rating_bucket, time_control
                    ORDER BY last_timestamp_ms
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                ) AS miss_rate_7,
                AVG(found::DOUBLE / NULLIF(total, 0)) OVER (
                    PARTITION BY source, motif, rating_bucket, time_control
                    ORDER BY last_timestamp_ms
                    ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                ) AS found_rate_30,
                AVG(missed::DOUBLE / NULLIF(total, 0)) OVER (
                    PARTITION BY source, motif, rating_bucket, time_control
                    ORDER BY last_timestamp_ms
                    ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                ) AS miss_rate_30
            FROM per_game
        ),
        trend_7 AS (
            SELECT
                source,
                'trend' AS metric_type,
                motif,
                7 AS window_days,
                trend_date,
                rating_bucket,
                time_control,
                total,
                found,
                missed,
                failed_attempt,
                unclear,
                found_rate_7 AS found_rate,
                miss_rate_7 AS miss_rate
            FROM rolling
        ),
        trend_30 AS (
            SELECT
                source,
                'trend' AS metric_type,
                motif,
                30 AS window_days,
                trend_date,
                rating_bucket,
                time_control,
                total,
                found,
                missed,
                failed_attempt,
                unclear,
                found_rate_30 AS found_rate,
                miss_rate_30 AS miss_rate
            FROM rolling
        ),
        time_trouble_inputs AS (
            SELECT
                source,
                time_control,
                result,
                clock_seconds,
                TRY_CAST(regexp_extract(time_control, '^(\\d+)', 1) AS DOUBLE)
                    AS initial_seconds
            FROM tactic_events
            WHERE clock_seconds IS NOT NULL
        ),
        time_trouble_scored AS (
            SELECT
                source,
                time_control,
                CASE
                    WHEN initial_seconds IS NULL OR initial_seconds <= 0 THEN NULL
                    ELSE LEAST(30.0, initial_seconds * 0.1)
                END AS threshold_seconds,
                CASE
                    WHEN initial_seconds IS NULL OR initial_seconds <= 0 THEN NULL
                    WHEN clock_seconds <= LEAST(30.0, initial_seconds * 0.1)
                    THEN 1
                    ELSE 0
                END AS time_trouble,
                CASE
                    WHEN result IN ('missed', 'failed_attempt') THEN 1
                    ELSE 0
                END AS missed_like
            FROM time_trouble_inputs
        ),
        time_trouble_metrics AS (
            SELECT
                source,
                'time_trouble_correlation' AS metric_type,
                'all' AS motif,
                NULL::INTEGER AS window_days,
                NULL::DATE AS trend_date,
                'all' AS rating_bucket,
                time_control,
                total,
                found,
                missed,
                0 AS failed_attempt,
                0 AS unclear,
                CASE
                    WHEN avg_time_trouble IS NULL
                        OR avg_missed IS NULL
                        OR avg_time_trouble IN (0, 1)
                        OR avg_missed IN (0, 1)
                    THEN NULL
                    ELSE (
                        avg_joint - (avg_time_trouble * avg_missed)
                    ) / SQRT(
                        (avg_time_trouble * (1 - avg_time_trouble))
                        * (avg_missed * (1 - avg_missed))
                    )
                END AS found_rate,
                avg_time_trouble AS miss_rate
            FROM (
                SELECT
                    source,
                    time_control,
                    COUNT(*) AS total,
                    SUM(CASE WHEN missed_like = 0 THEN 1 ELSE 0 END) AS found,
                    SUM(CASE WHEN missed_like = 1 THEN 1 ELSE 0 END) AS missed,
                    AVG(time_trouble::DOUBLE) AS avg_time_trouble,
                    AVG(missed_like::DOUBLE) AS avg_missed,
                    AVG((time_trouble * missed_like)::DOUBLE) AS avg_joint
                FROM time_trouble_scored
                WHERE time_trouble IS NOT NULL AND missed_like IS NOT NULL
                GROUP BY source, time_control
            ) stats
        ),
        unioned AS (
            SELECT
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
                found::DOUBLE / NULLIF(total, 0) AS found_rate,
                missed::DOUBLE / NULLIF(total, 0) AS miss_rate
            FROM breakdown
            UNION ALL
            SELECT
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
                found::DOUBLE / NULLIF(total, 0) AS found_rate,
                missed::DOUBLE / NULLIF(total, 0) AS miss_rate
            FROM breakdown_split
            UNION ALL
            SELECT
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
                miss_rate
            FROM trend_7
            UNION ALL
            SELECT
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
                miss_rate
            FROM trend_30
            UNION ALL
            SELECT
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
                miss_rate
            FROM time_trouble_metrics
        )
        SELECT
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
            CURRENT_TIMESTAMP AS updated_at
        FROM unioned
        """
    )


def _rows_to_dicts(
    result: duckdb.DuckDBPyConnection | duckdb.DuckDBPyRelation,
) -> list[dict[str, object]]:
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def _normalize_filter(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed or trimmed.lower() == "all":
        return None
    return trimmed


def _append_date_range_filters(
    conditions: list[str],
    params: list[object],
    start_date: datetime | None,
    end_date: datetime | None,
    column: str,
) -> None:
    """Append start/end date filters for a timestamp column using DATE casting."""
    if start_date:
        start_date_value = (
            start_date.date() if isinstance(start_date, datetime) else start_date
        )
        conditions.append(f"CAST({column} AS DATE) >= ?")
        params.append(start_date_value)
    if end_date:
        end_date_value = end_date.date() if isinstance(end_date, datetime) else end_date
        conditions.append(f"CAST({column} AS DATE) <= ?")
        params.append(end_date_value)


def _rating_bucket_clause(bucket: str) -> str:
    if bucket == "unknown":
        return "r.user_rating IS NULL"
    if bucket == "<1200":
        return "r.user_rating IS NOT NULL AND r.user_rating < 1200"
    if bucket == "1200-1399":
        return "r.user_rating >= 1200 AND r.user_rating < 1400"
    if bucket == "1400-1599":
        return "r.user_rating >= 1400 AND r.user_rating < 1600"
    if bucket == "1600-1799":
        return "r.user_rating >= 1600 AND r.user_rating < 1800"
    if bucket == "1800+":
        return "r.user_rating >= 1800"
    return "1 = 1"


def fetch_metrics(
    conn: duckdb.DuckDBPyConnection,
    source: str | None = None,
    motif: str | None = None,
    rating_bucket: str | None = None,
    time_control: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, object]]:
    normalized_motif = _normalize_filter(motif)
    normalized_rating = _normalize_filter(rating_bucket)
    normalized_time = _normalize_filter(time_control)

    query = "SELECT * FROM metrics_summary"
    params: list[object] = []
    conditions: list[str] = []
    if source:
        conditions.append("source = ?")
        params.append(source)
    if normalized_motif:
        conditions.append("motif = ?")
        params.append(normalized_motif)
    if normalized_rating:
        conditions.append("rating_bucket = ?")
        params.append(normalized_rating)
    if normalized_time:
        conditions.append("COALESCE(time_control, 'unknown') = ?")
        params.append(normalized_time)
    date_filters: list[str] = []
    if start_date:
        date_filters.append("trend_date >= ?")
        params.append(start_date)
    if end_date:
        date_filters.append("trend_date <= ?")
        params.append(end_date)
    if date_filters:
        conditions.append(f"(metric_type != 'trend' OR ({' AND '.join(date_filters)}))")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    result = conn.execute(query, params)
    return _rows_to_dicts(result)


def fetch_recent_games(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 20,
    source: str | None = None,
    rating_bucket: str | None = None,
    time_control: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    user: str | None = None,
) -> list[dict[str, object]]:
    normalized_rating = _normalize_filter(rating_bucket)
    normalized_time = _normalize_filter(time_control)
    query = """
        WITH latest_pgns AS (
            SELECT * EXCLUDE (rn)
            FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY game_id, source
                        ORDER BY pgn_version DESC
                    ) AS rn
                FROM raw_pgns
            )
            WHERE rn = 1
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
    if normalized_time:
        conditions.append("COALESCE(r.time_control, 'unknown') = ?")
        params.append(normalized_time)
    if normalized_rating:
        conditions.append(_rating_bucket_clause(normalized_rating))
    _append_date_range_filters(
        conditions,
        params,
        start_date,
        end_date,
        "to_timestamp(r.last_timestamp_ms / 1000)",
    )
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += "\n        )\n    "

    if source:
        filtered_conditions = " WHERE source = ?"
        params.append(source)
        final_query = (
            query
            + f"SELECT * FROM filtered{filtered_conditions} ORDER BY last_timestamp_ms DESC, game_id LIMIT ?"
        )
        params.append(limit)
    else:
        final_query = (
            query
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

    rows = _rows_to_dicts(conn.execute(final_query, params))
    return [_format_recent_game_row(row, user) for row in rows]


def _format_recent_game_row(
    row: Mapping[str, object], user: str | None
) -> dict[str, object]:
    raw_user = user or str(row.get("user") or "")
    metadata = BaseDbStore.extract_pgn_metadata(str(row.get("pgn") or ""), raw_user)
    user_lower = raw_user.lower()
    white = metadata.get("white_player")
    black = metadata.get("black_player")
    white_lower = str(white or "").lower()
    black_lower = str(black or "").lower()
    opponent = None
    user_color: str | None = None
    if white_lower and white_lower == user_lower:
        opponent = black
        user_color = "white"
    elif black_lower and black_lower == user_lower:
        opponent = white
        user_color = "black"
    else:
        opponent = black or white

    timestamp_ms = metadata.get("start_timestamp_ms")
    played_at = None
    if isinstance(timestamp_ms, (int, float)) and int(timestamp_ms) > 0:
        played_at = datetime.fromtimestamp(
            int(timestamp_ms) / 1000, tz=timezone.utc
        ).isoformat()
    else:
        fallback_ms = row.get("last_timestamp_ms")
        if isinstance(fallback_ms, (int, float)) and int(fallback_ms) > 0:
            played_at = datetime.fromtimestamp(
                int(fallback_ms) / 1000, tz=timezone.utc
            ).isoformat()

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
    limit: int = 20,
    source: str | None = None,
    rating_bucket: str | None = None,
    time_control: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, object]]:
    normalized_rating = _normalize_filter(rating_bucket)
    normalized_time = _normalize_filter(time_control)
    query = """
        WITH latest_pgns AS (
            SELECT * EXCLUDE (rn)
            FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY game_id, source
                        ORDER BY pgn_version DESC
                    ) AS rn
                FROM raw_pgns
            )
            WHERE rn = 1
        )
        SELECT p.*
        FROM positions p
        LEFT JOIN latest_pgns r ON r.game_id = p.game_id AND r.source = p.source
    """
    params: list[object] = []
    conditions: list[str] = []
    if source:
        conditions.append("p.source = ?")
        params.append(source)
    if normalized_time:
        conditions.append("COALESCE(r.time_control, 'unknown') = ?")
        params.append(normalized_time)
    if normalized_rating:
        conditions.append(_rating_bucket_clause(normalized_rating))
    _append_date_range_filters(
        conditions,
        params,
        start_date,
        end_date,
        "p.created_at",
    )
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY p.created_at DESC LIMIT ?"
    params.append(limit)
    result = conn.execute(query, params)
    return _rows_to_dicts(result)


def fetch_recent_tactics(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 20,
    source: str | None = None,
    motif: str | None = None,
    rating_bucket: str | None = None,
    time_control: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, object]]:
    normalized_motif = _normalize_filter(motif)
    normalized_rating = _normalize_filter(rating_bucket)
    normalized_time = _normalize_filter(time_control)
    query = """
        WITH latest_pgns AS (
            SELECT * EXCLUDE (rn)
            FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY game_id, source
                        ORDER BY pgn_version DESC
                    ) AS rn
                FROM raw_pgns
            )
            WHERE rn = 1
        )
        SELECT t.*, o.result, o.eval_delta, o.user_uci, p.source
        FROM tactics t
        LEFT JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
        LEFT JOIN positions p ON p.position_id = t.position_id
        LEFT JOIN latest_pgns r ON r.game_id = p.game_id AND r.source = p.source
    """
    params: list[object] = []
    conditions: list[str] = []
    if source:
        conditions.append("p.source = ?")
        params.append(source)
    if normalized_motif:
        conditions.append("t.motif = ?")
        params.append(normalized_motif)
    if normalized_time:
        conditions.append("COALESCE(r.time_control, 'unknown') = ?")
        params.append(normalized_time)
    if normalized_rating:
        conditions.append(_rating_bucket_clause(normalized_rating))
    _append_date_range_filters(
        conditions,
        params,
        start_date,
        end_date,
        "t.created_at",
    )
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY t.created_at DESC LIMIT ?"
    params.append(limit)
    result = conn.execute(query, params)
    return _rows_to_dicts(result)


def fetch_game_detail(
    conn: duckdb.DuckDBPyConnection,
    game_id: str,
    user: str,
    source: str | None = None,
) -> dict[str, object]:
    query = """
        WITH latest_pgns AS (
            SELECT * EXCLUDE (rn)
            FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY game_id, source
                        ORDER BY pgn_version DESC
                    ) AS rn
                FROM raw_pgns
            )
            WHERE rn = 1
        )
        SELECT *
        FROM latest_pgns
        WHERE game_id = ?
    """
    params: list[object] = [game_id]
    if source:
        query += " AND source = ?"
        params.append(source)
    result = conn.execute(query, params)
    row = result.fetchone()
    if not row and source:
        fallback_result = conn.execute(
            """
            WITH latest_pgns AS (
                SELECT * EXCLUDE (rn)
                FROM (
                    SELECT
                        *,
                        ROW_NUMBER() OVER (
                            PARTITION BY game_id, source
                            ORDER BY pgn_version DESC
                        ) AS rn
                    FROM raw_pgns
                )
                WHERE rn = 1
            )
            SELECT *
            FROM latest_pgns
            WHERE game_id = ?
            """,
            [game_id],
        )
        row = fallback_result.fetchone()
        if row:
            result = fallback_result
    if not row:
        return {
            "game_id": game_id,
            "source": source,
            "pgn": None,
            "metadata": {},
            "analysis": [],
        }
    columns = [desc[0] for desc in result.description]
    pgn_row = dict(zip(columns, row))
    pgn = pgn_row.get("pgn")
    metadata = BaseDbStore.extract_pgn_metadata(pgn or "", user)
    analysis_query = """
        SELECT
            t.tactic_id,
            t.position_id,
            t.game_id,
            t.motif,
            t.severity,
            t.best_uci,
            t.best_san,
            t.explanation,
            t.eval_cp,
            t.created_at,
            o.result,
            o.user_uci,
            o.eval_delta,
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
    analysis_rows = _rows_to_dicts(conn.execute(analysis_query, analysis_params))
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
    result = conn.execute(
        """
        SELECT
            t.tactic_id,
            t.game_id,
            t.position_id,
            t.motif,
            t.severity,
            t.best_uci,
            t.best_san,
            t.explanation,
            t.eval_cp,
            o.result,
            o.user_uci,
            o.eval_delta,
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


def grade_practice_attempt(
    conn: duckdb.DuckDBPyConnection,
    tactic_id: int,
    position_id: int,
    attempted_uci: str,
    latency_ms: int | None = None,
) -> dict[str, object]:
    tactic = fetch_practice_tactic(conn, tactic_id)
    if not tactic or tactic.get("position_id") != position_id:
        raise ValueError("Tactic not found for position")
    trimmed_attempt = attempted_uci.strip()
    if not trimmed_attempt:
        raise ValueError("attempted_uci is required")
    best_uci_raw = tactic.get("best_uci")
    best_uci = str(best_uci_raw).strip() if best_uci_raw is not None else ""
    correct = bool(best_uci) and trimmed_attempt.lower() == best_uci.lower()
    fen_value = tactic.get("fen")
    fen = str(fen_value) if fen_value is not None else None
    motif_value = tactic.get("motif")
    motif = str(motif_value) if motif_value is not None else None
    best_san = tactic.get("best_san")
    explanation = tactic.get("explanation")
    generated_san, generated_explanation = format_tactic_explanation(
        fen, best_uci, motif
    )
    if not best_san:
        best_san = generated_san
    if not explanation:
        explanation = generated_explanation
    attempt_id = record_training_attempt(
        conn,
        {
            "tactic_id": tactic_id,
            "position_id": position_id,
            "source": tactic.get("source"),
            "attempted_uci": trimmed_attempt,
            "correct": correct,
            "success": correct,
            "best_uci": best_uci,
            "motif": tactic.get("motif", "unknown"),
            "severity": tactic.get("severity", 0.0),
            "eval_delta": tactic.get("eval_delta", 0) or 0,
            "latency_ms": latency_ms,
        },
    )
    message = (
        f"Correct! {tactic.get('motif', 'tactic')} found."
        if correct
        else f"Missed it. Best move was {best_uci or '--'}."
    )
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
    results = ["missed"]
    if include_failed_attempt:
        results.append("failed_attempt")
    placeholders = ", ".join(["?"] * len(results))
    query = f"""
        SELECT
            t.tactic_id,
            t.game_id,
            t.position_id,
            t.motif,
            t.severity,
            t.best_uci,
            t.eval_cp,
            t.created_at,
            o.result,
            o.user_uci,
            o.eval_delta,
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
    version_row = conn.execute("SELECT version FROM metrics_version").fetchone()
    return int(version_row[0]) if version_row else 0
