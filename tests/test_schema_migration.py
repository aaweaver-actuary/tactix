import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tactix.db.duckdb_store import (
    SCHEMA_VERSION,
    _should_attempt_wal_recovery,
    get_connection,
    get_schema_version,
    migrate_schema,
)


class SchemaMigrationTests(unittest.TestCase):
    def test_migration_preserves_legacy_data(self) -> None:  # noqa: PLR0915
        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "tactix.duckdb")

        conn.execute(
            """
            CREATE TABLE raw_pgns (
                game_id TEXT,
                user TEXT,
                source TEXT,
                fetched_at TIMESTAMP,
                pgn TEXT,
                last_timestamp_ms BIGINT,
                cursor TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO raw_pgns
                (game_id, user, source, fetched_at, pgn, last_timestamp_ms, cursor)
            VALUES
                (
                    'game-1',
                    'lichess_user',
                    'lichess',
                    CURRENT_TIMESTAMP,
                    'PGN DATA',
                    123,
                    'cursor-1'
                )
            """
        )

        conn.execute(
            """
            CREATE TABLE positions (
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
            )
            """
        )
        conn.execute(
            """
            INSERT INTO positions
                (position_id, game_id, user, source, fen, ply, move_number, uci, san, clock_seconds)
            VALUES
                (1, 'game-1', 'lichess_user', 'lichess', 'fen', 3, 2, 'e2e4', 'e4', 120.5)
            """
        )

        migrate_schema(conn)

        self.assertEqual(get_schema_version(conn), SCHEMA_VERSION)

        raw_rows = conn.execute(
            "SELECT raw_pgn_id, game_id, pgn, pgn_version, last_timestamp_ms, cursor FROM raw_pgns"
        ).fetchall()
        self.assertEqual(len(raw_rows), 1)
        raw_pgn_id, game_id, pgn, version, last_ts, cursor = raw_rows[0]
        self.assertIsNotNone(raw_pgn_id)
        self.assertEqual(game_id, "game-1")
        self.assertEqual(pgn, "PGN DATA")
        self.assertEqual(version, 1)
        self.assertEqual(last_ts, 123)
        self.assertEqual(cursor, "cursor-1")

        positions_columns = {
            row[1] for row in conn.execute("PRAGMA table_info('positions')").fetchall()
        }
        self.assertIn("side_to_move", positions_columns)
        positions_row = conn.execute(
            """
            SELECT game_id, fen, ply, move_number, uci, san, clock_seconds, side_to_move
            FROM positions
            """
        ).fetchone()
        self.assertEqual(positions_row[0], "game-1")
        self.assertEqual(positions_row[1], "fen")
        self.assertEqual(positions_row[2], 3)
        self.assertEqual(positions_row[3], 2)
        self.assertEqual(positions_row[4], "e2e4")
        self.assertEqual(positions_row[5], "e4")
        self.assertEqual(positions_row[6], 120.5)
        self.assertIsNone(positions_row[7])

    def test_migration_upgrades_non_legacy_to_latest(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        conn = get_connection(tmp_dir / "tactix_latest.duckdb")

        migrate_schema(conn)

        self.assertEqual(get_schema_version(conn), SCHEMA_VERSION)
        columns = {row[1] for row in conn.execute("PRAGMA table_info('raw_pgns')").fetchall()}
        self.assertIn("raw_pgn_id", columns)
        self.assertIn("pgn_hash", columns)
        self.assertIn("pgn_version", columns)
        tactics_columns = {
            row[1] for row in conn.execute("PRAGMA table_info('tactics')").fetchall()
        }
        self.assertIn("best_san", tactics_columns)
        self.assertIn("explanation", tactics_columns)
        self.assertIn("tactic_piece", tactics_columns)
        self.assertIn("mate_type", tactics_columns)

    def test_should_attempt_wal_recovery_gate(self) -> None:
        exc = Exception("WAL replay failed")
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(_should_attempt_wal_recovery(exc))

        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"}, clear=True):
            self.assertTrue(_should_attempt_wal_recovery(exc))

        with patch.dict(os.environ, {"TACTIX_ENV": "dev"}, clear=True):
            self.assertTrue(_should_attempt_wal_recovery(exc))

        with patch.dict(os.environ, {"TACTIX_ALLOW_WAL_RECOVERY": "true"}, clear=True):
            self.assertTrue(_should_attempt_wal_recovery(exc))

        exc_no_wal = Exception("some other error")
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"}, clear=True):
            self.assertFalse(_should_attempt_wal_recovery(exc_no_wal))
