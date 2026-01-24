from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Iterable, List, Mapping

import duckdb

from tactix.logging_utils import get_logger

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
    uci TEXT,
    san TEXT,
    clock_seconds DOUBLE,
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
    motif TEXT,
    total BIGINT,
    found BIGINT,
    missed BIGINT,
    failed_attempt BIGINT,
    unclear BIGINT,
    updated_at TIMESTAMP
);
"""


def get_connection(db_path: Path) -> duckdb.DuckDBPyConnection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Opening DuckDB at %s", db_path)
    return duckdb.connect(str(db_path))


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(RAW_PGNS_SCHEMA)
    conn.execute(POSITIONS_SCHEMA)
    conn.execute(TACTICS_SCHEMA)
    conn.execute(TACTIC_OUTCOMES_SCHEMA)
    conn.execute(METRICS_VERSION_SCHEMA)
    conn.execute(METRICS_SUMMARY_SCHEMA)
    _ensure_raw_pgns_versioned(conn)
    _ensure_column(conn, "metrics_summary", "source", "TEXT")
    if conn.execute("SELECT COUNT(*) FROM metrics_version").fetchone()[0] == 0:
        conn.execute("INSERT INTO metrics_version VALUES (0, CURRENT_TIMESTAMP)")


def _hash_pgn(pgn: str) -> str:
    return hashlib.sha256(pgn.encode("utf-8")).hexdigest()


def _ensure_raw_pgns_versioned(conn: duckdb.DuckDBPyConnection) -> None:
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info('raw_pgns')").fetchall()
    }
    if "raw_pgn_id" not in columns:
        conn.execute("BEGIN TRANSACTION")
        try:
            existing_tables = {
                row[0]
                for row in conn.execute("SHOW TABLES").fetchall()
            }
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
                inserts.append(
                    (
                        next_id,
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        pgn_text,
                        _hash_pgn(pgn_text),
                        1,
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
                        ingested_at,
                        last_timestamp_ms,
                        cursor
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        next_id = conn.execute(
            "SELECT COALESCE(MAX(raw_pgn_id), 0) FROM raw_pgns"
        ).fetchone()[0]
        latest_cache: dict[tuple[str, str], tuple[str | None, int]] = {}
        inserted = 0
        for row in rows_list:
            game_id = str(row["game_id"])
            source = str(row["source"])
            pgn_text = str(row["pgn"])
            pgn_hash = _hash_pgn(pgn_text)
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
                    ingested_at,
                    last_timestamp_ms,
                    cursor
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    start_id = conn.execute(
        "SELECT COALESCE(MAX(position_id), 0) FROM positions"
    ).fetchone()[0]
    conn.execute("BEGIN TRANSACTION")
    position_ids: List[int] = []
    try:
        for idx, row in enumerate(rows_list, start=1):
            position_id = start_id + idx
            conn.execute(
                """
                INSERT INTO positions (position_id, game_id, user, source, fen, ply, move_number, uci, san, clock_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position_id,
                    row["game_id"],
                    row["user"],
                    row["source"],
                    row["fen"],
                    row["ply"],
                    row["move_number"],
                    row["uci"],
                    row.get("san", ""),
                    row.get("clock_seconds"),
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


def insert_tactics(
    conn: duckdb.DuckDBPyConnection,
    rows: Iterable[Mapping[str, object]],
) -> List[int]:
    rows_list = list(rows)
    if not rows_list:
        return []
    start_id = conn.execute(
        "SELECT COALESCE(MAX(tactic_id), 0) FROM tactics"
    ).fetchone()[0]
    conn.execute("BEGIN TRANSACTION")
    tactic_ids: List[int] = []
    try:
        for idx, row in enumerate(rows_list, start=1):
            tactic_id = start_id + idx
            conn.execute(
                """
                INSERT INTO tactics (tactic_id, game_id, position_id, motif, severity, best_uci, eval_cp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tactic_id,
                    row["game_id"],
                    row["position_id"],
                    row.get("motif", "unknown"),
                    row.get("severity", 0.0),
                    row.get("best_uci", ""),
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
    start_id = conn.execute(
        "SELECT COALESCE(MAX(outcome_id), 0) FROM tactic_outcomes"
    ).fetchone()[0]
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

        tactic_id = (
            conn.execute("SELECT COALESCE(MAX(tactic_id), 0) FROM tactics").fetchone()[
                0
            ]
            + 1
        )
        conn.execute(
            """
            INSERT INTO tactics (tactic_id, game_id, position_id, motif, severity, best_uci, eval_cp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tactic_id,
                tactic_row["game_id"],
                position_id,
                tactic_row.get("motif", "unknown"),
                tactic_row.get("severity", 0.0),
                tactic_row.get("best_uci", ""),
                tactic_row.get("eval_cp", 0),
            ),
        )
        outcome_id = (
            conn.execute(
                "SELECT COALESCE(MAX(outcome_id), 0) FROM tactic_outcomes"
            ).fetchone()[0]
            + 1
        )
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
    return conn.execute("SELECT version FROM metrics_version").fetchone()[0]


def update_metrics_summary(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("DELETE FROM metrics_summary")
    conn.execute(
        """
        INSERT INTO metrics_summary (source, motif, total, found, missed, failed_attempt, unclear, updated_at)
        SELECT
            COALESCE(p.source, 'unknown') AS source,
            t.motif,
            COUNT(*) AS total,
            SUM(CASE WHEN o.result = 'found' THEN 1 ELSE 0 END) AS found,
            SUM(CASE WHEN o.result = 'missed' THEN 1 ELSE 0 END) AS missed,
            SUM(CASE WHEN o.result = 'failed_attempt' THEN 1 ELSE 0 END) AS failed_attempt,
            SUM(CASE WHEN o.result = 'unclear' THEN 1 ELSE 0 END) AS unclear,
            CURRENT_TIMESTAMP AS updated_at
        FROM tactics t
        LEFT JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
        LEFT JOIN positions p ON p.position_id = t.position_id
        GROUP BY COALESCE(p.source, 'unknown'), t.motif
        """
    )


def _rows_to_dicts(result: duckdb.DuckDBPyRelation) -> list[dict[str, object]]:
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def fetch_metrics(
    conn: duckdb.DuckDBPyConnection, source: str | None = None
) -> list[dict[str, object]]:
    if source:
        result = conn.execute(
            "SELECT * FROM metrics_summary WHERE source = ?", [source]
        )
    else:
        result = conn.execute("SELECT * FROM metrics_summary")
    return _rows_to_dicts(result)


def fetch_recent_positions(
    conn: duckdb.DuckDBPyConnection, limit: int = 20, source: str | None = None
) -> list[dict[str, object]]:
    query = "SELECT * FROM positions"
    params: list[object] = []
    if source:
        query += " WHERE source = ?"
        params.append(source)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    result = conn.execute(query, params)
    return _rows_to_dicts(result)


def fetch_recent_tactics(
    conn: duckdb.DuckDBPyConnection, limit: int = 20, source: str | None = None
) -> list[dict[str, object]]:
    query = """
        SELECT t.*, o.result, o.eval_delta, o.user_uci, p.source
        FROM tactics t
        LEFT JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id
        LEFT JOIN positions p ON p.position_id = t.position_id
    """
    params: list[object] = []
    if source:
        query += " WHERE p.source = ?"
        params.append(source)
    query += " ORDER BY t.created_at DESC LIMIT ?"
    params.append(limit)
    result = conn.execute(query, params)
    return _rows_to_dicts(result)


def fetch_version(conn: duckdb.DuckDBPyConnection) -> int:
    return conn.execute("SELECT version FROM metrics_version").fetchone()[0]
