from pathlib import Path
import shutil
from tactix.config import Settings
from tactix.pipeline import run_daily_game_sync

fixture = Path("tests/fixtures/chesscom_correspondence_sample.pgn")
stockfish = Path(shutil.which("stockfish") or "stockfish")

for duckdb_path in [Path("client/data/tactix.duckdb"), Path("data/tactix.duckdb")]:
    checkpoint_label = "client" if duckdb_path.parts[0] == "client" else "data"
    checkpoint_path = Path(
        f"tmp-logs/feature_087_chesscom_since_{checkpoint_label}.txt"
    )
    analysis_checkpoint_path = Path(
        f"tmp-logs/analysis_checkpoint_feature_087_{checkpoint_label}.json"
    )
    metrics_path = duckdb_path.parent / "metrics_version.txt"
    settings = Settings(
        source="chesscom",
        chesscom_user="chesscom",
        chesscom_profile="correspondence",
        chesscom_token=None,
        duckdb_path=duckdb_path,
        metrics_version_file=metrics_path,
        chesscom_fixture_pgn_path=fixture,
        chesscom_use_fixture_when_no_token=True,
        use_fixture_when_no_token=True,
        stockfish_path=stockfish,
        stockfish_movetime_ms=60,
        stockfish_multipv=1,
        stockfish_depth=None,
        checkpoint_path=checkpoint_path,
        chesscom_checkpoint_path=checkpoint_path,
        analysis_checkpoint_path=analysis_checkpoint_path,
    )
    settings.apply_source_defaults()
    settings.apply_chesscom_profile("correspondence")
    settings.ensure_dirs()
    print(f"Seeding {duckdb_path}")
    print(run_daily_game_sync(settings, source="chesscom", profile="correspondence"))
