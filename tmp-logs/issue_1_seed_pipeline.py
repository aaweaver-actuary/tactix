from pathlib import Path
import shutil

from tactix.config import Settings
from tactix.pgn_utils import extract_last_timestamp_ms, split_pgn_chunks
from tactix.pipeline import run_daily_game_sync

USER = "groborger"
FIXTURE_PATH = Path("tests/fixtures/chesscom_2_bullet_games.pgn")


def main() -> None:
    stockfish_path = shutil.which("stockfish") or "stockfish"
    settings = Settings(
        source="chesscom",
        user=USER,
        chesscom_user=USER,
        chesscom_profile="bullet",
        chesscom_fixture_pgn_path=FIXTURE_PATH,
        chesscom_use_fixture_when_no_token=True,
        duckdb_path=Path("data/tactix.duckdb"),
        checkpoint_path=Path("data/chesscom_since_bullet.txt"),
        metrics_version_file=Path("data/metrics_version.txt"),
        stockfish_path=Path(stockfish_path),
        stockfish_movetime_ms=60,
        stockfish_depth=8,
        stockfish_multipv=2,
    )
    settings.apply_chesscom_profile("bullet")
    settings.chesscom_fixture_pgn_path = FIXTURE_PATH
    settings.fixture_pgn_path = FIXTURE_PATH

    pgn_text = FIXTURE_PATH.read_text()
    timestamps = [extract_last_timestamp_ms(chunk) for chunk in split_pgn_chunks(pgn_text)]
    window_start = min(timestamps) - 1000
    window_end = max(timestamps) + 1000

    run_daily_game_sync(
        settings,
        window_start_ms=window_start,
        window_end_ms=window_end,
    )

    print("Seeded Chess.com bullet fixture pipeline into", settings.duckdb_path)


if __name__ == "__main__":
    main()
