import unittest

from tactix.base_chess_client import (
    BaseChessClient,
    BaseChessClientContext,
    ChessFetchRequest,
)
from tactix.config import Settings
from tactix.logging_utils import get_logger


class DummyClient(BaseChessClient):
    def fetch_incremental_games(self, request: ChessFetchRequest):
        return self._build_fetch_result([], None, 0)


class BaseChessClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            user="tester",
            source="lichess",
            duckdb_path="/tmp/db.duckdb",
            checkpoint_path="/tmp/since.txt",
            metrics_version_file="/tmp/metrics.txt",
        )
        self.context = BaseChessClientContext(
            settings=self.settings, logger=get_logger("test")
        )

    def test_build_game_row_uses_settings(self) -> None:
        client = DummyClient(self.context)
        row = client._build_game_row("game-1", "[Event]\n", 123)
        self.assertEqual(row.game_id, "game-1")
        self.assertEqual(row.user, "tester")
        self.assertEqual(row.source, "lichess")
        self.assertEqual(row.last_timestamp_ms, 123)

    def test_build_fetch_result_payload(self) -> None:
        client = DummyClient(self.context)
        result = client._build_fetch_result([], None, 0)
        self.assertEqual(result.games, [])
        self.assertIsNone(result.next_cursor)
        self.assertEqual(result.last_timestamp_ms, 0)

    def test_base_client_requires_override(self) -> None:
        client = BaseChessClient(self.context)
        with self.assertRaises(NotImplementedError):
            client.fetch_incremental_games(ChessFetchRequest())


if __name__ == "__main__":
    unittest.main()
