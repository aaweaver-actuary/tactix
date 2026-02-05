from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tactix.config import Settings
from tactix.dashboard_query import DashboardQuery, clone_dashboard_query
from tactix.db._resolve_dashboard_query import _resolve_dashboard_query
from tactix.db.duckdb_dashboard_reader import (
    DuckDbDashboardDependencies,
    DuckDbDashboardFetchers,
    DuckDbDashboardReader,
)
from tactix.db.dashboard_repository_provider import (
    fetch_metrics,
    fetch_recent_games,
    fetch_recent_positions,
    fetch_recent_tactics,
)
from tactix.db.duckdb_store import (
    DuckDbStore,
    fetch_version,
    get_connection,
    init_schema,
    insert_positions,
    update_metrics_summary,
    upsert_tactic_with_outcome,
)
from tactix.db.raw_pgn_repository_provider import upsert_raw_pgns
from tactix.define_base_db_store_context__db_store import BaseDbStoreContext
from tactix.utils.logger import Logger

PGN_TEMPLATE = """[Event \"Test\"]
[Site \"https://lichess.org/AbcDef12\"]
[UTCDate \"2020.01.02\"]
[UTCTime \"03:04:05\"]
[White \"tester\"]
[Black \"opponent\"]
[WhiteElo \"{white_elo}\"]
[BlackElo \"{black_elo}\"]
[TimeControl \"{time_control}\"]
[Result \"*\"]

1. e4 *
"""


class DuckDbDashboardReaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.tmp_dir / "tactix.duckdb"
        self.conn = get_connection(self.db_path)
        init_schema(self.conn)
        self.settings = Settings(
            user="tester",
            source="lichess",
            duckdb_path=self.db_path,
            checkpoint_path=self.tmp_dir / "since.txt",
            metrics_version_file=self.tmp_dir / "metrics.txt",
        )

    def tearDown(self) -> None:
        self.conn.close()

    def test_reader_matches_store_for_single_source(self) -> None:
        self._insert_dashboard_rows("lichess", last_timestamp_ms=5)
        update_metrics_summary(self.conn)

        store = self._build_store()
        reader = self._build_reader()

        payload_store = store.get_dashboard_payload(source="lichess")
        payload_reader = reader.get_dashboard_payload(source="lichess")

        self.assertEqual(payload_reader, payload_store)
        self.assertEqual(payload_reader["source"], "lichess")

    def test_reader_matches_store_for_all_sources(self) -> None:
        sources = ["lichess", "chesscom"]
        for idx, source in enumerate(sources, start=1):
            self._insert_dashboard_rows(source, last_timestamp_ms=idx)
        update_metrics_summary(self.conn)

        store = self._build_store()
        reader = self._build_reader()

        payload_store = store.get_dashboard_payload(source=None)
        payload_reader = reader.get_dashboard_payload(DashboardQuery(source="all"))

        self.assertEqual(payload_reader, payload_store)
        self.assertEqual(payload_reader["source"], "all")

    def _build_store(self) -> DuckDbStore:
        return DuckDbStore(
            BaseDbStoreContext(settings=self.settings, logger=Logger("test")),
            db_path=self.settings.duckdb_path,
        )

    def _build_reader(self) -> DuckDbDashboardReader:
        dependencies = DuckDbDashboardDependencies(
            resolve_query=_resolve_dashboard_query,
            clone_query=clone_dashboard_query,
            fetchers=DuckDbDashboardFetchers(
                metrics=fetch_metrics,
                recent_games=fetch_recent_games,
                recent_positions=fetch_recent_positions,
                recent_tactics=fetch_recent_tactics,
            ),
            fetch_version=fetch_version,
            init_schema=init_schema,
        )
        return DuckDbDashboardReader(
            self.conn,
            user=self.settings.user,
            dependencies=dependencies,
        )

    def _insert_dashboard_rows(self, source: str, *, last_timestamp_ms: int) -> None:
        pgn = PGN_TEMPLATE.format(
            white_elo=1200 + last_timestamp_ms,
            black_elo=1300 + last_timestamp_ms,
            time_control="300+0",
        )
        upsert_raw_pgns(
            self.conn,
            [
                {
                    "game_id": f"game-{source}",
                    "user": self.settings.user,
                    "source": source,
                    "pgn": pgn,
                    "last_timestamp_ms": last_timestamp_ms,
                }
            ],
        )
        position_ids = insert_positions(
            self.conn,
            [
                {
                    "game_id": f"game-{source}",
                    "user": self.settings.user,
                    "source": source,
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
        upsert_tactic_with_outcome(
            self.conn,
            {
                "game_id": f"game-{source}",
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


if __name__ == "__main__":
    unittest.main()
