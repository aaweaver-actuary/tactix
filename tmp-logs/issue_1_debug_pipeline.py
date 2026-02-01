from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

from tactix.config import Settings
from tactix.db.duckdb_store import get_connection
from tactix.pipeline import run_daily_game_sync

fixture_path = Path("/Users/andy/tactix/tests/fixtures/chesscom_bullet_2026_02_01.pgn")

with tempfile.TemporaryDirectory() as tmp:
    tmp_dir = Path(tmp)
    settings = Settings(
        source="chesscom",
        chesscom_user="chesscom",
        chesscom_profile="bullet",
        duckdb_path=tmp_dir / "tactix_chesscom.duckdb",
        chesscom_checkpoint_path=tmp_dir / "chesscom_since_bullet.txt",
        metrics_version_file=tmp_dir / "metrics_chesscom.txt",
        chesscom_use_fixture_when_no_token=True,
        stockfish_path=Path("stockfish"),
        stockfish_movetime_ms=60,
        stockfish_depth=10,
        stockfish_multipv=1,
    )
    settings.apply_chesscom_profile("bullet")
    settings.chesscom_fixture_pgn_path = fixture_path

    window_start_ms = int(datetime(2026, 2, 1, tzinfo=UTC).timestamp() * 1000)
    window_end_ms = int(datetime(2026, 2, 2, tzinfo=UTC).timestamp() * 1000)

    result = run_daily_game_sync(
        settings,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
    )
    print("result", result)

    conn = get_connection(settings.duckdb_path)
    tactics = conn.execute(
        "SELECT t.game_id, t.motif, o.result, t.best_uci, o.user_uci, t.eval_cp, o.eval_delta FROM tactics t JOIN tactic_outcomes o ON o.tactic_id = t.tactic_id"
    ).fetchall()
    print("tactics", tactics)
    positions = conn.execute(
        "SELECT position_id, game_id, fen, uci, san FROM positions ORDER BY position_id"
    ).fetchall()
    print("positions", positions)
