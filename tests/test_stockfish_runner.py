import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import chess
import chess.engine

from tactix.config import Settings
from tactix.stockfish_runner import StockfishEngine


def test_analyse_fallback_material_score() -> None:
    settings = Settings()
    engine = StockfishEngine(settings)
    board = chess.Board()

    result = engine.analyse(board)

    assert result.best_move is None
    assert result.depth == 0
    assert result.score_cp == engine._material_score(board)


def test_resolve_command_prefers_existing_path() -> None:
    settings = Settings()
    with tempfile.NamedTemporaryFile() as handle:
        settings.stockfish_path = Path(handle.name)
        engine = StockfishEngine(settings)
        resolved = engine._resolve_command()

    assert resolved == str(settings.stockfish_path)


def test_resolve_command_uses_shutil_which() -> None:
    settings = Settings()
    settings.stockfish_path = Path("missing-stockfish")
    engine = StockfishEngine(settings)

    with (
        patch("tactix.stockfish_runner.Path.exists", return_value=False),
        patch("tactix.stockfish_runner.shutil.which", return_value="/usr/bin/stockfish"),
    ):
        resolved = engine._resolve_command()

    assert resolved == "/usr/bin/stockfish"
    assert settings.stockfish_path == Path("/usr/bin/stockfish")


def test_build_limit_prefers_depth() -> None:
    settings = Settings()
    engine = StockfishEngine(settings)

    settings.stockfish_depth = 12
    depth_limit = engine._build_limit()
    assert depth_limit.depth == 12

    settings.stockfish_depth = None
    settings.stockfish_movetime_ms = 250
    time_limit = engine._build_limit()
    assert time_limit.time == 0.25


def test_restart_handles_engine_quit_errors() -> None:
    settings = Settings()
    engine = StockfishEngine(settings)
    engine.engine = MagicMock()
    engine.engine.quit.side_effect = chess.engine.EngineError("boom")

    with patch.object(engine, "_start_engine") as start:
        engine.restart()

    start.assert_called_once()
