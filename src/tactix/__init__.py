"""TACTIX package entrypoints."""

from importlib import import_module
from typing import TYPE_CHECKING

from tactix.chess_game import ChessGame
from tactix.pipeline import run_daily_game_sync

chesscom_client = import_module("tactix.chess_clients.chesscom_client")
duckdb_store = import_module("tactix.db.duckdb_store")
lichess_client = import_module("tactix.chess_clients.lichess_client")


def main() -> None:
    """Run a single end-to-end pipeline execution."""
    result = run_daily_game_sync()
    print(result)


__all__ = [
    "ChessGame",
    "chesscom_client",
    "duckdb_store",
    "lichess_client",
    "main",
    "run_daily_game_sync",
]

if TYPE_CHECKING:
    from tactix.analyzer import TacticsAnalyzer
    from tactix.engine_result import EngineResult
    from tactix.get_material_value import get_material_value
    from tactix.models.chess_position import ChessPosition
    from tactix.PostgresSettings import PostgresSettings
    from tactix.refresh_metrics_result import RefreshMetricsResult

    _ = (
        TacticsAnalyzer,
        TacticsAnalyzer.analyze,
        EngineResult.empty,
        get_material_value,
        ChessPosition,
        PostgresSettings.is_configured,
        RefreshMetricsResult,
        RefreshMetricsResult.metrics_rows,
    )
