from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from tactix.analysis_context import AnalysisPositionContext, AnalysisPositionMeta, AnalysisPositionPersistence
from tactix.analysis_signature__pipeline import _analysis_signature
from tactix.app.use_cases.pipeline_support import _write_analysis_checkpoint
from tactix.config import Settings
from tactix.db.duckdb_store import init_schema
from tactix.db.position_repository_provider import insert_positions
from tactix.prepare_analysis_inputs__pipeline import _prepare_analysis_inputs
from tactix.process_analysis_position__pipeline import _process_analysis_position


def _build_game_row() -> dict[str, object]:
    pgn = (
        "[Event \"Test Game\"]\n"
        "[Site \"?\"]\n"
        "[Date \"2026.02.01\"]\n"
        "[Round \"-\"]\n"
        "[White \"user1\"]\n"
        "[Black \"user2\"]\n"
        "[Result \"1-0\"]\n\n"
        "1. e4 e5 2. Nf3 Nc6 1-0"
    )
    now = datetime.now(UTC)
    timestamp_ms = int(now.timestamp() * 1000)
    return {
        "game_id": "game-1",
        "user": "user1",
        "source": "lichess",
        "pgn": pgn,
        "fetched_at": now,
        "ingested_at": now,
        "last_timestamp_ms": timestamp_ms,
        "cursor": f"{timestamp_ms}:game-1",
    }


def _build_position() -> dict[str, object]:
    return {
        "game_id": "game-1",
        "user": "user1",
        "source": "lichess",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "ply": 0,
        "move_number": 1,
        "side_to_move": "white",
        "user_to_move": True,
        "uci": "e2e4",
        "san": "e4",
        "clock_seconds": None,
        "is_legal": True,
    }


def test_prepare_analysis_inputs_resumes_existing_positions() -> None:
    tmp_dir = Path(tempfile.mkdtemp())
    settings = Settings(
        user="user1",
        source="lichess",
        duckdb_path=tmp_dir / "tactix.duckdb",
        checkpoint_path=tmp_dir / "since.txt",
        metrics_version_file=tmp_dir / "metrics.txt",
        analysis_checkpoint_path=tmp_dir / "analysis_checkpoint.json",
    )
    conn = duckdb.connect(settings.duckdb_path)
    init_schema(conn)

    position = _build_position()
    position_ids = insert_positions(conn, [position])
    position["position_id"] = position_ids[0]

    analysis_signature = _analysis_signature(["game-1"], 1, settings.source)
    _write_analysis_checkpoint(settings.analysis_checkpoint_path, analysis_signature, 0)

    game_row = _build_game_row()
    result = _prepare_analysis_inputs(conn, settings, [game_row], progress=None, profile=None)

    assert result.positions
    assert result.resume_index == 0
    assert result.analysis_signature == analysis_signature
    assert result.raw_pgns_inserted >= 1

    conn.close()


def test_process_analysis_position_skips_resume_index() -> None:
    conn = duckdb.connect(":memory:")
    settings = Settings()
    context = AnalysisPositionContext(
        conn=conn,
        settings=settings,
        engine=None,
        meta=AnalysisPositionMeta(
            pos={},
            idx=0,
            resume_index=0,
            total_positions=1,
            progress_every=1,
        ),
        persistence=AnalysisPositionPersistence(
            analysis_checkpoint_path=None,
            analysis_signature="",
            pg_conn=None,
            analysis_pg_enabled=False,
        ),
        progress=None,
    )

    assert _process_analysis_position(context) == (0, 0)
    conn.close()
