"""TACTIX package entrypoints."""

from importlib import import_module

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
