from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tactix.db.duckdb_raw_pgn_repository import (
    DuckDbRawPgnRepository,
    default_raw_pgn_dependencies,
)
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.raw_pgn_repository_provider import (
    fetch_latest_pgn_hashes,
    fetch_latest_raw_pgns,
    fetch_raw_pgns_summary,
    upsert_raw_pgns,
)

PGN_BASE = """[Event \"Test\"]
[Site \"https://lichess.org/{game_id}\"]
[UTCDate \"2020.01.02\"]
[UTCTime \"03:04:05\"]
[White \"tester\"]
[Black \"opponent\"]
[WhiteElo \"1500\"]
[BlackElo \"1400\"]
[TimeControl \"300+0\"]
[Result \"1-0\"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 1-0
"""


class DuckDbRawPgnRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp_dir = Path(tempfile.mkdtemp())
        self.repo_conn = get_connection(tmp_dir / "repo.duckdb")
        self.fn_conn = get_connection(tmp_dir / "functions.duckdb")
        init_schema(self.repo_conn)
        init_schema(self.fn_conn)
        self.repo = DuckDbRawPgnRepository(
            self.repo_conn,
            dependencies=default_raw_pgn_dependencies(),
        )

    def tearDown(self) -> None:
        self.repo_conn.close()
        self.fn_conn.close()

    def test_repository_matches_duckdb_store_functions(self) -> None:
        rows = self._build_rows()
        inserted_repo = self.repo.upsert_raw_pgns(rows)
        inserted_functions = upsert_raw_pgns(self.fn_conn, rows)
        self.assertEqual(inserted_repo, inserted_functions)

        game_ids = [row["game_id"] for row in rows if row["source"] == "lichess"]
        hashes_repo = self.repo.fetch_latest_pgn_hashes(game_ids, source="lichess")
        hashes_functions = fetch_latest_pgn_hashes(self.fn_conn, game_ids, source="lichess")
        self.assertEqual(hashes_repo, hashes_functions)

        latest_repo = self._strip_timestamps(
            self.repo.fetch_latest_raw_pgns(source=None, limit=None)
        )
        latest_functions = self._strip_timestamps(
            fetch_latest_raw_pgns(self.fn_conn, source=None, limit=None)
        )
        self.assertEqual(latest_repo, latest_functions)

        summary_repo = self._normalize_summary(self.repo.fetch_raw_pgns_summary())
        summary_functions = self._normalize_summary(fetch_raw_pgns_summary(self.fn_conn))
        self.assertEqual(summary_repo, summary_functions)

    def _build_rows(self) -> list[dict[str, object]]:
        base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        modified_pgn = PGN_BASE + "5. O-O Be7 6. Re1 b5 1-0\n"
        return [
            {
                "game_id": "game-lichess",
                "user": "tester",
                "source": "lichess",
                "pgn": PGN_BASE.format(game_id="game-lichess"),
                "last_timestamp_ms": 10,
                "ingested_at": base_time,
            },
            {
                "game_id": "game-lichess",
                "user": "tester",
                "source": "lichess",
                "pgn": modified_pgn.format(game_id="game-lichess"),
                "last_timestamp_ms": 20,
                "ingested_at": base_time + timedelta(seconds=1),
            },
            {
                "game_id": "game-chesscom",
                "user": "tester",
                "source": "chesscom",
                "pgn": PGN_BASE.format(game_id="game-chesscom"),
                "last_timestamp_ms": 30,
                "ingested_at": base_time + timedelta(seconds=2),
            },
        ]

    def _strip_timestamps(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        keys_to_drop = {"ingested_at", "fetched_at"}
        return [
            {key: value for key, value in row.items() if key not in keys_to_drop} for row in rows
        ]

    def _normalize_summary(self, summary: dict[str, object]) -> dict[str, object]:
        normalized = dict(summary)
        normalized.pop("latest_ingested_at", None)
        normalized["sources"] = [
            {key: value for key, value in source.items() if key != "latest_ingested_at"}
            for source in summary.get("sources", [])
        ]
        return normalized


if __name__ == "__main__":
    unittest.main()
