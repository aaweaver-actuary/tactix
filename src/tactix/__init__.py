"""TACTIX package entrypoints."""

import sys
from importlib import import_module
from typing import TYPE_CHECKING

from tactix.chess_game import ChessGame
from tactix.pipeline import run_daily_game_sync
from tactix.sync_contexts import DailyGameSyncRequest

chesscom_client = import_module("tactix.chess_clients.chesscom_client")
duckdb_store = import_module("tactix.db.duckdb_store")
lichess_client = import_module("tactix.chess_clients.lichess_client")

_LEGACY_MODULE_ALIASES = {
    "tactix.DashboardQueryFilters": "tactix.dashboard_query_filters",
    "tactix.CLOCK_PARTS_SHORT": "tactix._normalize_clock_parts",
    "tactix.PGN_SCHEMA": "tactix.define_db_schemas__const",
    "tactix.NoGamesPayloadContext": "tactix.sync_contexts",
    "tactix.NoGamesAfterDedupePayloadContext_1": "tactix.sync_contexts",
    "tactix.duckdb_store": "tactix.db.duckdb_store",
}

for legacy_name, target in _LEGACY_MODULE_ALIASES.items():
    if legacy_name not in sys.modules:
        sys.modules[legacy_name] = import_module(target)


def main() -> None:
    """Run a single end-to-end pipeline execution."""
    result = run_daily_game_sync(DailyGameSyncRequest())
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
