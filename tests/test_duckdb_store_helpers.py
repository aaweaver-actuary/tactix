import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import duckdb

from tactix.duckdb_store import (
    _append_date_range_filters,
    _ensure_raw_pgns_versioned,
    _normalize_filter,
    _rating_bucket_clause,
    delete_game_rows,
    fetch_latest_pgn_hashes,
    fetch_latest_raw_pgns,
    fetch_metrics,
    fetch_position_counts,
    fetch_positions_for_games,
    fetch_recent_positions,
    fetch_recent_tactics,
    get_connection,
    grade_practice_attempt,
    hash_pgn,
    init_schema,
    insert_positions,
    insert_tactic_outcomes,
    insert_tactics,
    upsert_raw_pgns,
    upsert_tactic_with_outcome,
)


PGN_BASE = """[Event \"Test\"]
[Site \"https://lichess.org/AbcDef12\"]
[UTCDate \"2020.01.02\"]
[UTCTime \"03:04:05\"]
[White \"alice\"]
[Black \"bob\"]
[WhiteElo \"{white_elo}\"]
[BlackElo \"{black_elo}\"]
[TimeControl \"{time_control}\"]
[Result \"*\"]

1. e4 *
"""


class DuckdbStoreHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.conn = get_connection(self.tmp_dir / "tactix.duckdb")
        init_schema(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_fetch_latest_pgn_hashes_and_raw_pgns(self) -> None:
        pgn_v1 = PGN_BASE.format(white_elo=1300, black_elo=1400, time_control="300+0")
        pgn_v2 = pgn_v1 + "\n"
        rows = [
            {
                "game_id": "g1",
                "user": "alice",
                "source": "lichess",
                "pgn": pgn_v1,
                "last_timestamp_ms": 1,
            },
            {
                "game_id": "g1",
                "user": "alice",
                "source": "lichess",
                "pgn": pgn_v2,
                "last_timestamp_ms": 2,
            },
        ]
        upsert_raw_pgns(self.conn, rows)

        hashes = fetch_latest_pgn_hashes(self.conn, ["g1"], "lichess")
        self.assertEqual(hashes.get("g1"), hash_pgn(pgn_v2))

        latest = fetch_latest_raw_pgns(self.conn, source="lichess")
        self.assertEqual(len(latest), 1)
        self.assertEqual(latest[0]["pgn"], pgn_v2)

        limited = fetch_latest_raw_pgns(self.conn, source="lichess", limit=1)
        self.assertEqual(len(limited), 1)

    def test_append_date_range_filters_casts_datetime_values(self) -> None:
        conditions: list[str] = []
        params: list[object] = []
        start_date = datetime(2024, 1, 2, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 5, tzinfo=timezone.utc)

        _append_date_range_filters(
            conditions,
            params,
            start_date,
            end_date,
            "p.created_at",
        )

        self.assertEqual(
            conditions,
            [
                "CAST(p.created_at AS DATE) >= ?",
                "CAST(p.created_at AS DATE) <= ?",
            ],
        )
        self.assertEqual(params, [start_date.date(), end_date.date()])

    def test_empty_helpers_short_circuit(self) -> None:
        self.assertEqual(upsert_raw_pgns(self.conn, []), 0)
        self.assertEqual(fetch_latest_pgn_hashes(self.conn, [], "lichess"), {})
        self.assertEqual(fetch_position_counts(self.conn, [], "lichess"), {})
        self.assertEqual(fetch_positions_for_games(self.conn, []), [])
        self.assertEqual(insert_positions(self.conn, []), [])
        insert_tactic_outcomes(self.conn, [])
        delete_game_rows(self.conn, [])

    def test_insert_positions_and_delete_game_rows(self) -> None:
        pgn = PGN_BASE.format(white_elo=1200, black_elo=1400, time_control="300+0")
        upsert_raw_pgns(
            self.conn,
            [
                {
                    "game_id": "g2",
                    "user": "alice",
                    "source": "lichess",
                    "pgn": pgn,
                    "last_timestamp_ms": 5,
                }
            ],
        )
        positions = [
            {
                "game_id": "g2",
                "user": "alice",
                "source": "lichess",
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                "ply": 1,
                "move_number": 1,
                "side_to_move": "black",
                "uci": "e2e4",
                "san": "e4",
                "clock_seconds": 300,
                "is_legal": True,
            }
        ]
        position_ids = insert_positions(self.conn, positions)
        tactic_id = upsert_tactic_with_outcome(
            self.conn,
            {
                "game_id": "g2",
                "position_id": position_ids[0],
                "motif": "fork",
                "severity": 1.2,
                "best_uci": "e2e4",
                "best_san": "e4",
                "explanation": "test",
                "eval_cp": 50,
            },
            {
                "result": "found",
                "user_uci": "e2e4",
                "eval_delta": 0,
            },
        )
        self.assertGreater(tactic_id, 0)

        delete_game_rows(self.conn, ["g2"])
        remaining_positions = self.conn.execute(
            "SELECT COUNT(*) FROM positions WHERE game_id = ?",
            ["g2"],
        ).fetchone()[0]
        remaining_tactics = self.conn.execute(
            "SELECT COUNT(*) FROM tactics WHERE game_id = ?",
            ["g2"],
        ).fetchone()[0]
        remaining_outcomes = self.conn.execute(
            "SELECT COUNT(*) FROM tactic_outcomes WHERE tactic_id = ?",
            [tactic_id],
        ).fetchone()[0]

        self.assertEqual(remaining_positions, 0)
        self.assertEqual(remaining_tactics, 0)
        self.assertEqual(remaining_outcomes, 0)

    def test_insert_tactics_and_outcomes(self) -> None:
        pgn = PGN_BASE.format(white_elo=1200, black_elo=1400, time_control="300+0")
        upsert_raw_pgns(
            self.conn,
            [
                {
                    "game_id": "g5",
                    "user": "alice",
                    "source": "lichess",
                    "pgn": pgn,
                    "last_timestamp_ms": 10,
                }
            ],
        )
        position_ids = insert_positions(
            self.conn,
            [
                {
                    "game_id": "g5",
                    "user": "alice",
                    "source": "lichess",
                    "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                    "ply": 1,
                    "move_number": 1,
                    "side_to_move": "black",
                    "uci": "e2e4",
                    "san": "e4",
                    "clock_seconds": 300,
                    "is_legal": True,
                }
            ],
        )
        tactic_ids = insert_tactics(
            self.conn,
            [
                {
                    "game_id": "g5",
                    "position_id": position_ids[0],
                    "motif": "fork",
                    "severity": 1.0,
                    "best_uci": "e2e4",
                    "best_san": "e4",
                    "explanation": "test",
                    "eval_cp": 10,
                }
            ],
        )
        insert_tactic_outcomes(
            self.conn,
            [
                {
                    "tactic_id": tactic_ids[0],
                    "result": "found",
                    "user_uci": "e2e4",
                    "eval_delta": 0,
                }
            ],
        )
        count = self.conn.execute("SELECT COUNT(*) FROM tactic_outcomes").fetchone()[0]
        self.assertEqual(count, 1)

    def test_upsert_raw_pgns_persists_hash_and_metadata(self) -> None:
        lichess_pgn = PGN_BASE.format(
            white_elo=1500,
            black_elo=1400,
            time_control="300+0",
        )
        chesscom_pgn = """[Event \"Test\"]
[Site \"https://www.chess.com/game/live/123456789\"]
[UTCDate \"2020.02.03\"]
[UTCTime \"03:04:05\"]
[White \"alice\"]
[Black \"bob\"]
[WhiteElo \"1550\"]
[BlackElo \"1450\"]
[TimeControl \"600+0\"]
[Result \"*\"]

1. d4 *
"""

        rows = [
            {
                "game_id": "lichess-1",
                "user": "alice",
                "source": "lichess",
                "pgn": lichess_pgn,
                "last_timestamp_ms": 1,
            },
            {
                "game_id": "chesscom-1",
                "user": "alice",
                "source": "chesscom",
                "pgn": chesscom_pgn,
                "last_timestamp_ms": 2,
            },
        ]

        upsert_raw_pgns(self.conn, rows)

        results = self.conn.execute(
            "SELECT game_id, source, pgn_hash, time_control, user_rating FROM raw_pgns"
        ).fetchall()
        rows_by_key = {(row[0], row[1]): row for row in results}

        lichess_row = rows_by_key[("lichess-1", "lichess")]
        self.assertEqual(lichess_row[2], hash_pgn(lichess_pgn))
        self.assertEqual(lichess_row[3], "300+0")
        self.assertEqual(lichess_row[4], 1500)

        chesscom_row = rows_by_key[("chesscom-1", "chesscom")]
        self.assertEqual(chesscom_row[2], hash_pgn(chesscom_pgn))
        self.assertEqual(chesscom_row[3], "600+0")
        self.assertEqual(chesscom_row[4], 1550)

    def test_metrics_filters_and_rating_bucket_clause(self) -> None:
        self.assertIsNone(_normalize_filter("all"))
        self.assertIsNone(_normalize_filter(""))
        self.assertEqual(_rating_bucket_clause("unknown"), "r.user_rating IS NULL")
        self.assertEqual(
            _rating_bucket_clause("<1200"),
            "r.user_rating IS NOT NULL AND r.user_rating < 1200",
        )
        self.assertEqual(
            _rating_bucket_clause("1800+"),
            "r.user_rating >= 1800",
        )

        trend_date = datetime.now(tz=timezone.utc).date()
        self.conn.execute(
            "INSERT INTO metrics_summary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            [
                "lichess",
                "trend",
                "fork",
                7,
                trend_date,
                "1200-1399",
                "300+0",
                1,
                1,
                0,
                0,
                0,
                1.0,
                0.0,
            ],
        )
        start_date = datetime.combine(
            trend_date, datetime.min.time(), tzinfo=timezone.utc
        ) - timedelta(days=1)
        end_date = datetime.combine(
            trend_date, datetime.min.time(), tzinfo=timezone.utc
        ) + timedelta(days=1)
        rows = fetch_metrics(
            self.conn,
            source="lichess",
            motif="fork",
            rating_bucket="1200-1399",
            time_control="300+0",
            start_date=start_date,
            end_date=end_date,
        )
        self.assertEqual(len(rows), 1)

    def test_fetch_recent_positions_and_tactics_filters(self) -> None:
        pgn_fast = PGN_BASE.format(white_elo=1300, black_elo=1500, time_control="300+0")
        pgn_slow = PGN_BASE.format(white_elo=1900, black_elo=2000, time_control="600+0")
        now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        upsert_raw_pgns(
            self.conn,
            [
                {
                    "game_id": "g3",
                    "user": "alice",
                    "source": "lichess",
                    "pgn": pgn_fast,
                    "last_timestamp_ms": now_ms,
                },
                {
                    "game_id": "g4",
                    "user": "alice",
                    "source": "lichess",
                    "pgn": pgn_slow,
                    "last_timestamp_ms": now_ms + 1,
                },
            ],
        )

        positions = [
            {
                "game_id": "g3",
                "user": "alice",
                "source": "lichess",
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                "ply": 1,
                "move_number": 1,
                "side_to_move": "black",
                "uci": "e2e4",
                "san": "e4",
                "clock_seconds": 300,
                "is_legal": True,
            },
            {
                "game_id": "g4",
                "user": "alice",
                "source": "lichess",
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                "ply": 1,
                "move_number": 1,
                "side_to_move": "black",
                "uci": "e2e4",
                "san": "e4",
                "clock_seconds": 600,
                "is_legal": True,
            },
        ]
        position_ids = insert_positions(self.conn, positions)

        upsert_tactic_with_outcome(
            self.conn,
            {
                "game_id": "g3",
                "position_id": position_ids[0],
                "motif": "fork",
                "severity": 1.0,
                "best_uci": "e2e4",
                "best_san": "e4",
                "explanation": "fast",
                "eval_cp": 30,
            },
            {"result": "found", "user_uci": "e2e4", "eval_delta": 0},
        )
        upsert_tactic_with_outcome(
            self.conn,
            {
                "game_id": "g4",
                "position_id": position_ids[1],
                "motif": "mate",
                "severity": 2.0,
                "best_uci": "e2e4",
                "best_san": "e4",
                "explanation": "slow",
                "eval_cp": 80,
            },
            {"result": "missed", "user_uci": "d2d4", "eval_delta": -50},
        )

        start_date = datetime.now(tz=timezone.utc) - timedelta(days=1)
        end_date = datetime.now(tz=timezone.utc) + timedelta(days=1)
        recent_positions = fetch_recent_positions(
            self.conn,
            limit=10,
            source="lichess",
            rating_bucket="1200-1399",
            time_control="300+0",
            start_date=start_date,
            end_date=end_date,
        )
        self.assertEqual(len(recent_positions), 1)
        self.assertEqual(recent_positions[0]["game_id"], "g3")

        recent_tactics = fetch_recent_tactics(
            self.conn,
            limit=10,
            source="lichess",
            motif="fork",
            rating_bucket="1200-1399",
            time_control="300+0",
            start_date=start_date,
            end_date=end_date,
        )
        self.assertEqual(len(recent_tactics), 1)
        self.assertEqual(recent_tactics[0]["motif"], "fork")

    def test_grade_practice_attempt_errors(self) -> None:
        with self.assertRaises(ValueError):
            grade_practice_attempt(
                self.conn, tactic_id=999, position_id=1, attempted_uci="e2e4"
            )

        pgn = PGN_BASE.format(white_elo=1200, black_elo=1400, time_control="300+0")
        upsert_raw_pgns(
            self.conn,
            [
                {
                    "game_id": "g6",
                    "user": "alice",
                    "source": "lichess",
                    "pgn": pgn,
                    "last_timestamp_ms": 2,
                }
            ],
        )
        position_ids = insert_positions(
            self.conn,
            [
                {
                    "game_id": "g6",
                    "user": "alice",
                    "source": "lichess",
                    "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                    "ply": 1,
                    "move_number": 1,
                    "side_to_move": "black",
                    "uci": "e2e4",
                    "san": "e4",
                    "clock_seconds": 300,
                    "is_legal": True,
                }
            ],
        )
        tactic_id = upsert_tactic_with_outcome(
            self.conn,
            {
                "game_id": "g6",
                "position_id": position_ids[0],
                "motif": "fork",
                "severity": 1.0,
                "best_uci": "e2e4",
                "best_san": "e4",
                "explanation": "",
                "eval_cp": 10,
            },
            {"result": "found", "user_uci": "e2e4", "eval_delta": 0},
        )

        with self.assertRaises(ValueError):
            grade_practice_attempt(
                self.conn,
                tactic_id=tactic_id,
                position_id=position_ids[0],
                attempted_uci=" ",
            )

    def test_upsert_tactic_requires_position_id(self) -> None:
        with self.assertRaises(ValueError):
            upsert_tactic_with_outcome(
                self.conn, {"game_id": "g7"}, {"result": "found"}
            )

    def test_ensure_raw_pgns_versioned_legacy(self) -> None:
        legacy_conn = get_connection(self.tmp_dir / "legacy.duckdb")
        legacy_conn.execute(
            "CREATE TABLE raw_pgns (game_id TEXT, user TEXT, source TEXT, fetched_at TIMESTAMP, pgn TEXT, last_timestamp_ms BIGINT, cursor TEXT)"
        )
        legacy_conn.execute("CREATE TABLE raw_pgns_legacy (game_id TEXT)")
        pgn = PGN_BASE.format(white_elo=1200, black_elo=1300, time_control="300+0")
        legacy_conn.execute(
            "INSERT INTO raw_pgns VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?)",
            ["g8", "alice", "lichess", pgn, 3, "cursor"],
        )

        _ensure_raw_pgns_versioned(legacy_conn)

        columns = {
            row[1]
            for row in legacy_conn.execute("PRAGMA table_info('raw_pgns')").fetchall()
        }
        self.assertIn("raw_pgn_id", columns)
        count = legacy_conn.execute("SELECT COUNT(*) FROM raw_pgns").fetchone()[0]
        self.assertEqual(count, 1)
        legacy_conn.close()

    def test_get_connection_wal_recovery(self) -> None:
        db_path = self.tmp_dir / "wal_test.duckdb"
        wal_path = db_path.with_name(f"{db_path.name}.wal")
        wal_path.write_text("wal")

        real_connect = duckdb.connect
        connection = MagicMock()

        def _fake_connect(path: str):
            if _fake_connect.calls == 0:
                _fake_connect.calls += 1
                raise duckdb.InternalException("wal error")
            return connection

        _fake_connect.calls = 0

        with patch("tactix.duckdb_store.duckdb.connect", side_effect=_fake_connect):
            conn = get_connection(db_path)

        self.assertIs(conn, connection)
        self.assertFalse(wal_path.exists())


if __name__ == "__main__":
    unittest.main()
