"""TACTIX package entrypoints."""

from tactix.pipeline import run_daily_game_sync


def main() -> None:
    """Run a single end-to-end pipeline execution."""
    result = run_daily_game_sync()
    print(result)
