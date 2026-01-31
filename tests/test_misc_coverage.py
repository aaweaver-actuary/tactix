import unittest

import chess

from tactix.engine_result import EngineResult
from tactix.get_material_value import get_material_value
from tactix.models.chess_position import ChessPosition
from tactix.PostgresSettings import PostgresSettings
from tactix.refresh_metrics_result import RefreshMetricsResult


class MiscCoverageTests(unittest.TestCase):
    def test_get_material_value(self) -> None:
        self.assertEqual(get_material_value("q"), 900)
        self.assertEqual(get_material_value(chess.KNIGHT), 300)
        with self.assertRaises(ValueError):
            get_material_value("unknown")

    def test_chess_position_model(self) -> None:
        position = ChessPosition(fen=chess.Board().fen(), turn=chess.WHITE)
        self.assertEqual(position.turn, chess.WHITE)

    def test_refresh_metrics_result_model(self) -> None:
        result = RefreshMetricsResult(
            source="lichess",
            user="tester",
            metrics_version=1,
            metrics_rows=42,
        )
        self.assertEqual(result.metrics_rows, 42)

    def test_postgres_settings_is_configured(self) -> None:
        settings = PostgresSettings(dsn="postgres://localhost/test")
        self.assertTrue(settings.is_configured)

    def test_engine_result_empty(self) -> None:
        result = EngineResult.empty()
        self.assertEqual(result.score_cp, 0)


if __name__ == "__main__":
    unittest.main()
